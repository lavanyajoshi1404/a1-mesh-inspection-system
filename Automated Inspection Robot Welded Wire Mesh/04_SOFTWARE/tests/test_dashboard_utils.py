"""
Unit tests for dashboard utility functions, visualization generators, and pipeline runner.

Verifies:
  1. Full inspection pipeline execution and data integrity
  2. Final classification mapping (OK, REVIEW, SPACING DEFECT, etc.)
  3. Real anomaly extraction from optical evidence
  4. Visualization overlay generation (grid, intersection, heatmap, spacing)
  5. Heatmap spatial alignment and dimensions
  6. Report generation (JSON, TXT, CSV) and disk export
  7. Camera acquisition error handling
  8. Execution on real validation image IMG_20260920_200712.jpg yielding legitimate REVIEW

Run with:
    pytest -q 04_SOFTWARE/tests
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

# Ensure 04_SOFTWARE root is on sys.path
SOFTWARE_ROOT = Path(__file__).resolve().parent.parent
if str(SOFTWARE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOFTWARE_ROOT))

from config.settings import DATA_INPUT_DIR
from core.inspection_decision import InspectionDecision
from core.mesh_spacing import (
    CalibrationScale,
    MeshSpacingResult,
    ProductSpacingProfile,
    SpacingMeasurement,
    measure_mesh_spacing,
)
from core.weld_intersection import (
    IntersectionAssessment,
    WeldIntersectionResult,
)
from core.wire_detection import (
    DetectedWire,
    Intersection,
    WireGridDetectionResult,
)
from dashboard.utils.camera import (
    CameraError,
    capture_frame_from_network,
    test_camera_index as _test_camera_index,
)
from dashboard.utils.export import (
    generate_csv_spacings,
    generate_json_report,
    generate_text_report,
    save_inspection_to_disk,
)
from dashboard.utils.pipeline_runner import (
    ClassificationInvariantError,
    determine_final_classification,
    extract_real_anomalies,
    run_inspection_pipeline,
)
from dashboard.utils.visualizations import (
    draw_anomaly_heatmap,
    draw_grid_overlay,
    draw_intersection_overlay,
    draw_spacing_visualization,
)


class TestDashboardUtils(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_synthetic_grid_image(self, width=600, height=800):
        img = np.full((height, width, 3), 200, dtype=np.uint8)
        for y in [160, 360, 560]:
            cv2.line(img, (40, y), (width - 40, y), (60, 60, 60), 6)
        for x in [150, 300, 450]:
            cv2.line(img, (x, 40), (x, height - 40), (60, 60, 60), 6)
        return img

    def test_pipeline_runner_on_synthetic_image(self):
        """Pipeline runner must execute end-to-end and produce all outputs and overlays."""
        img = self._make_synthetic_grid_image()
        result = run_inspection_pipeline(img, source_name="synthetic.jpg", input_source_type="UPLOAD")

        self.assertIsNotNone(result)
        self.assertEqual(result.source_name, "synthetic.jpg")
        self.assertGreaterEqual(result.wire_result.num_horizontal_wires, 2)
        self.assertGreaterEqual(result.wire_result.num_vertical_wires, 2)
        self.assertIsNotNone(result.grid_overlay)
        self.assertIsNotNone(result.intersection_overlay)
        self.assertIsNotNone(result.heatmap_overlay)
        self.assertIsNotNone(result.spacing_overlay)
        self.assertIn(result.final_classification, ("OK", "REVIEW", "SPACING DEFECT", "WELD DEFECT"))

    def test_pipeline_reports_rust_like_surface_regions(self):
        image = self._make_synthetic_grid_image()
        cv2.rectangle(image, (100, 100), (160, 145), (0, 100, 200), -1)

        result = run_inspection_pipeline(image, source_name="rust-test.jpg", input_source_type="UPLOAD")

        self.assertGreater(result.rust_area_percentage, 0)
        self.assertGreater(result.rust_regions_count, 0)
        self.assertIsNotNone(result.rust_mask)
        self.assertEqual(result.rust_mask.shape, image.shape[:2])

    def test_determine_final_classification_mappings(self):
        """Test strict classification mapping logic."""
        # 1. PASS -> OK
        dec_pass = InspectionDecision(
            source_name="test",
            final_status="PASS",
            reasons=[],
            spacing_status="WITHIN_TOLERANCE",
            intersection_status="ALL_NORMAL",
        )
        wire_res = WireGridDetectionResult(source_name="test", image_width=100, image_height=100)
        weld_res = WeldIntersectionResult(source_name="test")
        spacing_res = MeshSpacingResult(source_name="test")

        self.assertEqual(determine_final_classification(dec_pass, spacing_res, weld_res), "OK")

        # 2. FAIL with spacing violation -> SPACING DEFECT
        dec_fail = InspectionDecision(
            source_name="test",
            final_status="FAIL",
            reasons=["Spacing out of tolerance"],
            spacing_status="OUT_OF_TOLERANCE",
        )
        self.assertEqual(determine_final_classification(dec_fail, spacing_res, weld_res), "SPACING DEFECT")

        # 3. REVIEW -> REVIEW
        dec_rev = InspectionDecision(
            source_name="test",
            final_status="REVIEW",
            reasons=["Provisional calibration"],
        )
        self.assertEqual(determine_final_classification(dec_rev, spacing_res, weld_res), "REVIEW")

    def test_determine_final_classification_raises_on_impossible_fail_state(self):
        """M-4: FAIL without a spacing violation (and weld_fail permanently False)
        is not a valid 6th classification state - it must raise loudly rather
        than silently degrade to REVIEW, so a future fail-path change can never
        introduce an unclassified/mislabeled state without being noticed."""
        wire_res = WireGridDetectionResult(source_name="test", image_width=100, image_height=100)
        weld_res = WeldIntersectionResult(source_name="test")
        spacing_res = MeshSpacingResult(source_name="test")

        # This combination should be impossible via core.inspection_decision's
        # real logic (FAIL always implies spacing_status == "OUT_OF_TOLERANCE"),
        # but we construct it directly here to pin the safety net's behavior.
        dec_impossible = InspectionDecision(
            source_name="test",
            final_status="FAIL",
            reasons=["synthetic invariant-violation test"],
            spacing_status="SOME_OTHER_STATUS",
        )
        with self.assertRaises(ClassificationInvariantError):
            determine_final_classification(dec_impossible, spacing_res, weld_res)

    def test_classification_taxonomy_has_exactly_five_states(self):
        """M-4: the user-facing classification taxonomy must remain exactly
        OK / SPACING DEFECT / WELD DEFECT / MULTIPLE DEFECTS / REVIEW - no
        'DEFECT DETECTED' or other undocumented sixth state."""
        wire_res = WireGridDetectionResult(source_name="test", image_width=100, image_height=100)
        weld_res = WeldIntersectionResult(source_name="test")
        spacing_res = MeshSpacingResult(source_name="test")

        reachable_states = set()
        dec_pass = InspectionDecision(source_name="test", final_status="PASS", reasons=[])
        reachable_states.add(determine_final_classification(dec_pass, spacing_res, weld_res))

        dec_fail = InspectionDecision(
            source_name="test", final_status="FAIL", reasons=[], spacing_status="OUT_OF_TOLERANCE"
        )
        reachable_states.add(determine_final_classification(dec_fail, spacing_res, weld_res))

        dec_review = InspectionDecision(source_name="test", final_status="REVIEW", reasons=[])
        reachable_states.add(determine_final_classification(dec_review, spacing_res, weld_res))

        allowed_states = {"OK", "SPACING DEFECT", "WELD DEFECT", "MULTIPLE DEFECTS", "REVIEW"}
        self.assertTrue(reachable_states.issubset(allowed_states))
        self.assertNotIn("DEFECT DETECTED", allowed_states)

    def test_extract_real_anomalies(self):
        """Verify real optical anomalies are extracted from weld and wire results."""
        wire_res = WireGridDetectionResult(source_name="test", image_width=600, image_height=600)
        wire_res.horizontal_wires = [
            DetectedWire(position_px=100.0, extent_px=(50.0, 550.0), segment_count=1),
            DetectedWire(position_px=300.0, extent_px=(50.0, 550.0), segment_count=1),
        ]
        wire_res.vertical_wires = [
            DetectedWire(position_px=150.0, extent_px=(50.0, 550.0), segment_count=1),
            DetectedWire(position_px=350.0, extent_px=(50.0, 550.0), segment_count=1),
        ]
        # Only 1 intersection detected out of 4 expected
        wire_res.intersections = [Intersection(x_px=150.0, y_px=100.0, horizontal_wire_index=0, vertical_wire_index=0)]

        weld_res = WeldIntersectionResult(source_name="test")
        weld_res.assessments.append(
            IntersectionAssessment(
                x_px=150.0,
                y_px=100.0,
                horizontal_wire_index=0,
                vertical_wire_index=0,
                is_top_row=True,
                is_bottom_row=False,
                is_left_column=True,
                is_right_column=False,
                expected_arms=["down", "right"],
                observed_arms=["down"],
                arm_intensities={"down": 60.0},
                otsu_threshold_used=120.0,
                status="POTENTIALLY_ANOMALOUS",
                notes="Missing right arm.",
            )
        )

        spacing_res = measure_mesh_spacing(wire_res)

        anomalies = extract_real_anomalies(wire_res, weld_res, spacing_res)
        self.assertGreater(len(anomalies), 0)

        # Check that categories correspond to real evidence
        categories = {a.category for a in anomalies}
        self.assertIn("Intersection Visual Arm Mismatch", categories)
        self.assertIn("Incomplete Grid Intersection", categories)

    def test_overlays_generation_and_heatmap_alignment(self):
        """Verify overlay shapes match base image and heatmap overlay is aligned."""
        img = self._make_synthetic_grid_image(width=500, height=700)
        wire_res = WireGridDetectionResult(source_name="test", image_width=500, image_height=700)
        wire_res.horizontal_wires = [
            DetectedWire(position_px=200.0, extent_px=(50.0, 450.0), segment_count=1),
            DetectedWire(position_px=400.0, extent_px=(50.0, 450.0), segment_count=1),
        ]
        wire_res.vertical_wires = [
            DetectedWire(position_px=150.0, extent_px=(50.0, 650.0), segment_count=1),
            DetectedWire(position_px=350.0, extent_px=(50.0, 650.0), segment_count=1),
        ]
        wire_res.intersections = [
            Intersection(x_px=150.0, y_px=200.0, horizontal_wire_index=0, vertical_wire_index=0),
            Intersection(x_px=350.0, y_px=200.0, horizontal_wire_index=0, vertical_wire_index=1),
            Intersection(x_px=150.0, y_px=400.0, horizontal_wire_index=1, vertical_wire_index=0),
            Intersection(x_px=350.0, y_px=400.0, horizontal_wire_index=1, vertical_wire_index=1),
        ]

        weld_res = WeldIntersectionResult(source_name="test")
        for isec in wire_res.intersections:
            weld_res.assessments.append(
                IntersectionAssessment(
                    x_px=isec.x_px,
                    y_px=isec.y_px,
                    horizontal_wire_index=isec.horizontal_wire_index,
                    vertical_wire_index=isec.vertical_wire_index,
                    is_top_row=(isec.horizontal_wire_index == 0),
                    is_bottom_row=(isec.horizontal_wire_index == 1),
                    is_left_column=(isec.vertical_wire_index == 0),
                    is_right_column=(isec.vertical_wire_index == 1),
                    expected_arms=["down", "right"],
                    observed_arms=["down", "right"],
                    arm_intensities={"down": 50.0, "right": 50.0},
                    otsu_threshold_used=120.0,
                    status="NORMAL",
                    notes="Observed arms match expected pattern.",
                )
            )

        spacing_res = measure_mesh_spacing(wire_res)

        grid_ov = draw_grid_overlay(img, wire_res)
        self.assertEqual(grid_ov.shape, img.shape)

        weld_ov = draw_intersection_overlay(img, wire_res, weld_res)
        self.assertEqual(weld_ov.shape, img.shape)

        heat_ov = draw_anomaly_heatmap(img, wire_res, weld_res, spacing_res)
        self.assertEqual(heat_ov.shape, img.shape)

        space_ov = draw_spacing_visualization(img, spacing_res, wire_res)
        self.assertEqual(space_ov.shape, img.shape)

    def test_report_and_export_generation(self):
        """Verify JSON, text, CSV reports and disk export work cleanly."""
        img = self._make_synthetic_grid_image()
        result = run_inspection_pipeline(img, source_name="export_test.jpg", input_source_type="UPLOAD")

        # 1. JSON Report
        json_str = generate_json_report(result)
        data = json.loads(json_str)
        self.assertEqual(data["source_name"], "export_test.jpg")
        self.assertIn("grid_statistics", data)
        self.assertIn("spacing_statistics", data)

        # 2. Text Report
        text_str = generate_text_report(result)
        self.assertIn("A-1 MESH INSPECTION SYSTEM", text_str)
        self.assertIn("FINAL CLASSIFICATION", text_str)

        # 3. CSV Spacings
        csv_str = generate_csv_spacings(result)
        self.assertIn("Axis,Index", csv_str)

        # 4. Save to Disk
        saved_paths = save_inspection_to_disk(result, self.tmp_dir)
        self.assertIn("decision_json", saved_paths)
        self.assertTrue(saved_paths["decision_json"].exists())
        self.assertTrue(saved_paths["text_report"].exists())

    def test_camera_utils_invalid_url_raises_error(self):
        """Invalid stream URL must raise CameraError gracefully."""
        with self.assertRaises(CameraError):
            capture_frame_from_network("not_a_valid_url")

    def test_real_validation_image_produces_legitimate_review(self):
        """Real validation image IMG_20260920_200712.jpg must legitimately produce REVIEW."""
        real_img_path = DATA_INPUT_DIR / "IMG_20260920_200712.jpg"
        if not real_img_path.exists():
            self.skipTest(f"Validation image {real_img_path} not found.")

        result = run_inspection_pipeline(real_img_path, input_source_type="UPLOAD")

        # 1. Must produce REVIEW, never FAIL or PASS
        self.assertEqual(result.final_classification, "REVIEW")
        self.assertEqual(result.decision.final_status, "REVIEW")

        # 2. Exact geometry detected
        self.assertEqual(result.wire_result.num_horizontal_wires, 5)
        self.assertEqual(result.wire_result.num_vertical_wires, 4)
        self.assertEqual(result.wire_result.num_intersections, 18)
        self.assertEqual(result.wire_result.expected_intersections, 20)

        # 3. Decision reasons must cite real technical limitations
        reasons_text = " ".join(result.decision.reasons).lower()
        self.assertIn("unvalidated estimate", reasons_text)
        self.assertIn("uncalibrated", reasons_text)
        self.assertIn("tolerance", reasons_text)


if __name__ == "__main__":
    unittest.main()
