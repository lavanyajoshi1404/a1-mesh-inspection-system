"""
Milestone 6 tests for core.mesh_spacing.

Verifies:
  1. Pixel spacing measurement between adjacent detected wires along both axes.
  2. Conversion to millimeters using calibration.
  3. Default vertical calibration uses a fixed 11.0 px/mm scale estimate
     (status: UNVALIDATED ESTIMATE - not a passed core.calibration validation run).
  4. Default horizontal calibration preserves documented position-dependent limitation
     (status: UNCALIBRATED, mm is None).
  5. Reporting of all required fields: measured spacing, pixel spacing, calibration used,
     axis, location/index, and status (CALIBRATED, PROVISIONAL, UNVALIDATED ESTIMATE,
     or UNCALIBRATED).
  6. Strict avoidance of invented A-1 product tolerances in standard reference profiles.
  7. Strict avoidance of defect claims when spacing differs from reference profiles.
  8. Configurable product profile and tolerance comparison.
  9. Robustness on invalid inputs, empty grids, single wires, and unsorted wires.
  10. JSON serialization of results.
  11. End-to-end integration with core.wire_detection.

Run with:
    python -m unittest discover -s tests
(from the 04_SOFTWARE/ directory)
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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.calibration import CalibrationResult
from core.mesh_spacing import (
    STANDARD_PROFILES,
    CalibrationScale,
    MeshSpacingError,
    MeshSpacingResult,
    ProductSpacingProfile,
    SpacingMeasurement,
    compare_against_profile,
    draw_mesh_spacing_overlay,
    measure_mesh_spacing,
    save_mesh_spacing_result,
)
from core.wire_detection import DetectedWire, WireGridDetectionResult, detect_wire_grid


def _make_synthetic_wire_result(
    h_ys=(100.0, 250.0, 400.0, 600.0),
    v_xs=(150.0, 450.0, 750.0),
    source_name="synthetic_grid.jpg",
) -> WireGridDetectionResult:
    """Helper to build a factual WireGridDetectionResult with known coordinates."""
    res = WireGridDetectionResult(
        source_name=source_name,
        image_width=1000,
        image_height=1000,
    )
    for y in h_ys:
        res.horizontal_wires.append(
            DetectedWire(position_px=float(y), extent_px=(100.0, 900.0), segment_count=5)
        )
    for x in v_xs:
        res.vertical_wires.append(
            DetectedWire(position_px=float(x), extent_px=(50.0, 950.0), segment_count=5)
        )
    return res


class TestMeshSpacing(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_invalid_input_raises_mesh_spacing_error(self):
        """None or non-WireGridDetectionResult must raise MeshSpacingError."""
        with self.assertRaises(MeshSpacingError):
            measure_mesh_spacing(None)  # type: ignore

        with self.assertRaises(MeshSpacingError):
            measure_mesh_spacing("not_a_wire_result")  # type: ignore

    def test_empty_grid_returns_zero_spacings_without_error(self):
        """An edge image with no detected wires produces 0 spacings, not an exception."""
        empty_res = WireGridDetectionResult(source_name="empty.jpg", image_width=800, image_height=600)
        res = measure_mesh_spacing(empty_res)
        self.assertEqual(res.num_vertical_spacings, 0)
        self.assertEqual(res.num_horizontal_spacings, 0)
        self.assertIsNone(res.mean_vertical_spacing_px)
        self.assertIsNone(res.mean_horizontal_spacing_px)

    def test_single_wire_returns_zero_spacings(self):
        """Single wire has no adjacent neighbor, so spacing cannot be computed."""
        res_one = WireGridDetectionResult(source_name="single.jpg", image_width=800, image_height=600)
        res_one.horizontal_wires.append(DetectedWire(position_px=100.0, extent_px=(0.0, 800.0), segment_count=1))
        res = measure_mesh_spacing(res_one)
        self.assertEqual(res.num_vertical_spacings, 0)

    def test_pixel_spacing_measured_accurately(self):
        """Adjacent wire differences in pixel space must be exactly w[i+1] - w[i]."""
        wire_res = _make_synthetic_wire_result(
            h_ys=(100.0, 250.0, 450.0),  # diffs: 150.0, 200.0
            v_xs=(50.0, 180.0, 320.0),   # diffs: 130.0, 140.0
        )
        res = measure_mesh_spacing(wire_res)

        self.assertEqual(res.num_vertical_spacings, 2)
        self.assertEqual(res.num_horizontal_spacings, 2)

        # Check vertical spacings (Y-separation between horizontal wires)
        self.assertAlmostEqual(res.vertical_spacings[0].pixel_spacing, 150.0, places=2)
        self.assertAlmostEqual(res.vertical_spacings[0].location_px, 175.0, places=2)
        self.assertEqual(res.vertical_spacings[0].wire_index_1, 0)
        self.assertEqual(res.vertical_spacings[0].wire_index_2, 1)

        self.assertAlmostEqual(res.vertical_spacings[1].pixel_spacing, 200.0, places=2)
        self.assertAlmostEqual(res.vertical_spacings[1].location_px, 350.0, places=2)

        # Check horizontal spacings (X-separation between vertical wires)
        self.assertAlmostEqual(res.horizontal_spacings[0].pixel_spacing, 130.0, places=2)
        self.assertAlmostEqual(res.horizontal_spacings[0].location_px, 115.0, places=2)
        self.assertAlmostEqual(res.horizontal_spacings[1].pixel_spacing, 140.0, places=2)
        self.assertAlmostEqual(res.horizontal_spacings[1].location_px, 250.0, places=2)

    def test_vertical_calibration_defaults_to_fixed_estimate_11_px_per_mm(self):
        """Default vertical calibration must use 11.0 px/mm with UNVALIDATED ESTIMATE status."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 210.0))  # 110 px diff
        res = measure_mesh_spacing(wire_res)

        self.assertEqual(res.num_vertical_spacings, 1)
        s = res.vertical_spacings[0]

        # 110 px / 11.0 px/mm = 10.0 mm
        self.assertAlmostEqual(s.pixel_spacing, 110.0, places=2)
        self.assertIsNotNone(s.measured_spacing)
        self.assertAlmostEqual(s.measured_spacing, 10.0, places=2)
        self.assertEqual(s.calibration_used, 11.0)
        self.assertEqual(s.calibration_status, "UNVALIDATED ESTIMATE")
        self.assertEqual(s.axis, "vertical")

    def test_horizontal_calibration_preserves_uncalibrated_limitation_by_default(self):
        """Default horizontal calibration must preserve documented limitation (UNCALIBRATED, mm=None)."""
        wire_res = _make_synthetic_wire_result(v_xs=(200.0, 450.0))  # 250 px diff
        res = measure_mesh_spacing(wire_res)

        self.assertEqual(res.num_horizontal_spacings, 1)
        s = res.horizontal_spacings[0]

        self.assertAlmostEqual(s.pixel_spacing, 250.0, places=2)
        self.assertIsNone(s.measured_spacing)
        self.assertIsNone(s.calibration_used)
        self.assertEqual(s.calibration_status, "UNCALIBRATED")
        self.assertEqual(s.axis, "horizontal")
        self.assertIn("limitation", s.notes.lower())

    def test_all_six_required_report_fields_present_on_each_measurement(self):
        """Requirements: measured spacing, pixel spacing, calibration used,
        axis, location/index, and status (CALIBRATED, PROVISIONAL,
        UNVALIDATED ESTIMATE, or UNCALIBRATED)."""
        wire_res = _make_synthetic_wire_result()
        res = measure_mesh_spacing(wire_res)

        for s in res.all_spacings:
            # 1. measured spacing
            self.assertTrue(hasattr(s, "measured_spacing"))
            # 2. pixel spacing
            self.assertGreater(s.pixel_spacing, 0)
            # 3. calibration used
            self.assertTrue(hasattr(s, "calibration_used"))
            # 4. axis
            self.assertIn(s.axis, ("vertical", "horizontal"))
            # 5. location/index
            self.assertIsInstance(s.index, int)
            self.assertGreater(s.location_px, 0)
            self.assertIsInstance(s.wire_index_1, int)
            self.assertIsInstance(s.wire_index_2, int)
            # 6. whether CALIBRATED, PROVISIONAL, UNVALIDATED ESTIMATE, or UNCALIBRATED
            self.assertIn(
                s.calibration_status,
                ("CALIBRATED", "PROVISIONAL", "UNVALIDATED ESTIMATE", "UNCALIBRATED"),
            )

    def test_custom_calibrated_scale_reports_calibrated_status(self):
        """When an authoritative 2D calibration is provided, status is CALIBRATED."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 200.0), v_xs=(100.0, 200.0))
        cal_scale = CalibrationScale(px_per_mm=10.0, status="CALIBRATED", source="2D_target_calibration")

        res = measure_mesh_spacing(wire_res, calibration_vertical=cal_scale, calibration_horizontal=cal_scale)

        self.assertEqual(res.vertical_spacings[0].calibration_status, "CALIBRATED")
        self.assertAlmostEqual(res.vertical_spacings[0].measured_spacing, 10.0, places=2)
        self.assertEqual(res.horizontal_spacings[0].calibration_status, "CALIBRATED")
        self.assertAlmostEqual(res.horizontal_spacings[0].measured_spacing, 10.0, places=2)

    def test_calibration_result_integration_from_core_calibration(self):
        """Integration with core.calibration.CalibrationResult object."""
        wire_res = _make_synthetic_wire_result(h_ys=(0.0, 220.0))
        m3_cal = CalibrationResult(
            source_name="ruler.jpg",
            axis="vertical",
            roi=(0, 100, 0, 1000),
            status="VALIDATED_SINGLE_AXIS_PROVISIONAL",
            px_per_mm=11.0,
            mm_per_tick_assumed=1.0,
            ticks_detected=50,
            spacings_px=[11] * 49,
            inlier_count=49,
            inlier_fraction=1.0,
            inlier_cv=0.01,
            drift_correlation=0.05,
            notes="Milestone 3 validated provisional ruler calibration.",
        )

        res = measure_mesh_spacing(wire_res, calibration_vertical=m3_cal)
        self.assertEqual(res.vertical_spacings[0].calibration_status, "PROVISIONAL")
        self.assertAlmostEqual(res.vertical_spacings[0].measured_spacing, 20.0, places=2)

    def test_unsorted_wires_are_properly_ordered(self):
        """Input wires out of coordinate order must be sorted so spacing is between neighbors."""
        res_raw = WireGridDetectionResult(source_name="scrambled.jpg", image_width=800, image_height=800)
        # Out of order: 300, 100, 200
        res_raw.horizontal_wires = [
            DetectedWire(position_px=300.0, extent_px=(0.0, 800.0), segment_count=1),
            DetectedWire(position_px=100.0, extent_px=(0.0, 800.0), segment_count=1),
            DetectedWire(position_px=200.0, extent_px=(0.0, 800.0), segment_count=1),
        ]
        res = measure_mesh_spacing(res_raw)
        self.assertEqual(res.num_vertical_spacings, 2)
        # Both intervals must be 100 px (100->200 and 200->300), not negative
        self.assertAlmostEqual(res.vertical_spacings[0].pixel_spacing, 100.0)
        self.assertAlmostEqual(res.vertical_spacings[1].pixel_spacing, 100.0)

    def test_standard_profiles_do_not_invent_tolerances(self):
        """Engineering principle: standard reference profiles must have tolerances=None."""
        for pid, prof in STANDARD_PROFILES.items():
            self.assertIsNone(
                prof.vertical_tolerance_mm,
                f"Profile {pid} must not invent vertical_tolerance_mm",
            )
            self.assertIsNone(
                prof.horizontal_tolerance_mm,
                f"Profile {pid} must not invent horizontal_tolerance_mm",
            )
            self.assertIsNotNone(prof.nominal_vertical_spacing_mm)
            self.assertIsNotNone(prof.nominal_horizontal_spacing_mm)

    def test_profile_comparison_without_tolerances_does_not_invent_pass_fail(self):
        """Comparing against standard profile with no tolerance reports facts, never FAIL or DEFECTIVE."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 375.0))  # 275 px / 11 px/mm = 25.0 mm
        spacing_res = measure_mesh_spacing(wire_res)

        # Profile P001 has nominal vertical 12.7 mm, tolerance None
        profile_p001 = STANDARD_PROFILES["P001"]
        comp = compare_against_profile(spacing_res, profile_p001)

        self.assertEqual(len(comp.comparisons), spacing_res.num_vertical_spacings + spacing_res.num_horizontal_spacings)
        v_comp = comp.comparisons[0]
        self.assertEqual(v_comp.status, "NO_TOLERANCE_CONFIGURED")
        self.assertNotIn("DEFECTIVE", v_comp.status)
        self.assertNotEqual(v_comp.status, "FAIL")
        self.assertNotEqual(v_comp.status, "PASS")
        self.assertAlmostEqual(v_comp.deviation_mm, 25.0 - 12.7, places=2)

    def test_profile_comparison_with_explicit_tolerance_and_calibrated_scale(self):
        """A genuinely CALIBRATED scale + configured tolerance evaluates within/out
        of tolerance without defect labeling. Uses an explicit CALIBRATED
        CalibrationScale (not the UNVALIDATED ESTIMATE default) - see
        test_unvalidated_estimate_cannot_produce_within_tolerance below for the
        C-1 safety check on the default path."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 232.0))  # 132 px
        cal = CalibrationScale(px_per_mm=11.0, status="CALIBRATED", source="test_fixture")
        spacing_res = measure_mesh_spacing(wire_res, calibration_vertical=cal)  # 132/11 = 12.0 mm

        custom_profile = ProductSpacingProfile(
            profile_id="CUSTOM_TEST",
            name="Custom Test Profile",
            nominal_vertical_spacing_mm=12.7,
            vertical_tolerance_mm=1.0,  # 12.7 ± 1.0 -> 11.7 to 13.7
        )

        comp = compare_against_profile(spacing_res, custom_profile)
        v_comp = comp.comparisons[0]
        self.assertEqual(v_comp.status, "WITHIN_TOLERANCE")
        self.assertAlmostEqual(v_comp.deviation_mm, -0.7, places=2)

    def test_profile_comparison_with_explicit_tolerance_and_provisional_scale(self):
        """A genuinely validated PROVISIONAL scale (e.g. a passed core.calibration
        single-axis run) must still be usable for tolerance comparison - C-1 only
        excludes UNVALIDATED ESTIMATE / UNCALIBRATED, not a real PROVISIONAL result."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 232.0))  # 132 px
        cal = CalibrationScale(px_per_mm=11.0, status="PROVISIONAL", source="test_fixture")
        spacing_res = measure_mesh_spacing(wire_res, calibration_vertical=cal)  # 12.0 mm

        custom_profile = ProductSpacingProfile(
            profile_id="CUSTOM_TEST",
            name="Custom Test Profile",
            nominal_vertical_spacing_mm=12.7,
            vertical_tolerance_mm=1.0,
        )
        comp = compare_against_profile(spacing_res, custom_profile)
        v_comp = comp.comparisons[0]
        self.assertEqual(v_comp.status, "WITHIN_TOLERANCE")

    def test_unvalidated_estimate_cannot_produce_within_tolerance(self):
        """C-1: the default UNVALIDATED ESTIMATE scale (11.0 px/mm) must NEVER
        produce WITHIN_TOLERANCE, even when it numerically falls inside the
        configured tolerance band. A numeric measured_spacing value alone is
        not sufficient evidence for a tolerance judgement."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 232.0))  # 132 px / 11.0 = 12.0 mm
        spacing_res = measure_mesh_spacing(wire_res)  # default: UNVALIDATED ESTIMATE

        # 12.0 mm numerically falls well inside 12.7 +/- 1.0 (11.7-13.7) -
        # if the old bug were present this would wrongly report WITHIN_TOLERANCE.
        custom_profile = ProductSpacingProfile(
            profile_id="CUSTOM_TEST",
            name="Custom Test Profile",
            nominal_vertical_spacing_mm=12.7,
            vertical_tolerance_mm=1.0,
        )
        comp = compare_against_profile(spacing_res, custom_profile)
        v_comp = comp.comparisons[0]
        self.assertEqual(v_comp.status, "UNVALIDATED_CALIBRATION")
        self.assertNotEqual(v_comp.status, "WITHIN_TOLERANCE")
        self.assertNotEqual(v_comp.status, "OUT_OF_TOLERANCE")
        # The numeric deviation is still reported as a fact, just not used for a verdict.
        self.assertIsNotNone(v_comp.deviation_mm)

    def test_unvalidated_estimate_cannot_produce_out_of_tolerance(self):
        """C-1: the default UNVALIDATED ESTIMATE scale must never produce
        OUT_OF_TOLERANCE either, even when it numerically falls outside the
        configured tolerance band."""
        wire_res = _make_synthetic_wire_result(h_ys=(100.0, 375.0))  # 275 px / 11.0 = 25.0 mm
        spacing_res = measure_mesh_spacing(wire_res)  # default: UNVALIDATED ESTIMATE

        # 25.0 mm is far outside 12.7 +/- 1.0 - if the old bug were present this
        # would wrongly report OUT_OF_TOLERANCE (a false SPACING DEFECT trigger).
        custom_profile = ProductSpacingProfile(
            profile_id="CUSTOM_TEST",
            name="Custom Test Profile",
            nominal_vertical_spacing_mm=12.7,
            vertical_tolerance_mm=1.0,
        )
        comp = compare_against_profile(spacing_res, custom_profile)
        v_comp = comp.comparisons[0]
        self.assertEqual(v_comp.status, "UNVALIDATED_CALIBRATION")
        self.assertNotEqual(v_comp.status, "WITHIN_TOLERANCE")
        self.assertNotEqual(v_comp.status, "OUT_OF_TOLERANCE")

    def test_save_mesh_spacing_result_writes_readable_json(self):
        """save_mesh_spacing_result produces a valid JSON file containing all required fields."""
        wire_res = _make_synthetic_wire_result()
        res = measure_mesh_spacing(wire_res)

        out_path = save_mesh_spacing_result(res, self.tmp_dir)
        self.assertTrue(out_path.exists())

        with open(out_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["source_name"], res.source_name)
        self.assertEqual(data["num_vertical_spacings"], res.num_vertical_spacings)
        self.assertEqual(data["num_horizontal_spacings"], res.num_horizontal_spacings)
        self.assertEqual(len(data["vertical_spacings"]), res.num_vertical_spacings)
        self.assertEqual(len(data["horizontal_spacings"]), res.num_horizontal_spacings)
        self.assertIn("mean_vertical_spacing_mm", data)

    def test_end_to_end_with_wire_detection(self):
        """Integration test: detect_wire_grid -> measure_mesh_spacing together."""
        # Draw a synthetic grid image following test_wire_detection conventions
        width, height = 600, 800
        img = np.full((height, width, 3), 200, dtype=np.uint8)
        h_ys = [160, 360, 560]
        v_xs = [150, 300, 450]
        for y in h_ys:
            cv2.line(img, (40, y), (width - 40, y), (60, 60, 60), 6)
        for x in v_xs:
            cv2.line(img, (x, 40), (x, height - 40), (60, 60, 60), 6)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        wire_res = detect_wire_grid(edges, "e2e_grid.jpg")

        self.assertGreaterEqual(wire_res.num_horizontal_wires, 2)
        self.assertGreaterEqual(wire_res.num_vertical_wires, 2)

        spacing_res = measure_mesh_spacing(wire_res)
        self.assertGreater(spacing_res.num_vertical_spacings, 0)
        self.assertGreater(spacing_res.num_horizontal_spacings, 0)

        # Spacings should be ~200 px vertical, ~150 px horizontal
        self.assertAlmostEqual(spacing_res.mean_vertical_spacing_px, 200.0, delta=10.0)
        self.assertAlmostEqual(spacing_res.mean_horizontal_spacing_px, 150.0, delta=10.0)

        # Overlay generation
        overlay = draw_mesh_spacing_overlay(img, spacing_res, wire_res)
        self.assertEqual(overlay.shape[:2], img.shape[:2])


if __name__ == "__main__":
    unittest.main()
