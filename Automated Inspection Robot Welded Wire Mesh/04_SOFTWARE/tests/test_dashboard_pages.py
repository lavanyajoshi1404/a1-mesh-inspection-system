"""
Unit tests for dashboard multi-page architecture, component contracts, and navigation pages.

Verifies:
  1. All 6 application page components import cleanly and are callable.
  2. NAV_PAGES and PAGE_LABELS contain exact required pages and numbering.
  3. Real validation image produces legitimate REVIEW result consistent with engineering rules.
  4. Centralized classification presentation handles OK, SPACING DEFECT, WELD DEFECT, MULTIPLE DEFECTS, REVIEW.
  5. MeshSpacingResult attribute safety (no profile_comparison AttributeError).
  6. Graceful handling of missing/None optional fields without exceptions.
"""

import sys
import unittest
from pathlib import Path

# Ensure 04_SOFTWARE root is on sys.path
SOFTWARE_ROOT = Path(__file__).resolve().parent.parent
if str(SOFTWARE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOFTWARE_ROOT))

import cv2
import numpy as np
from config.settings import DATA_INPUT_DIR
from core.mesh_spacing import (
    MeshSpacingResult,
    ProductSpacingProfile,
    SpacingMeasurement,
    STANDARD_PROFILES,
    compare_against_profile,
)
from dashboard.app import NAV_PAGES, PAGE_LABELS
from dashboard.components.architecture import render_system_architecture
from dashboard.components.measurements_page import render_measurements_page
from dashboard.components.new_inspection_view import render_new_inspection_page
from dashboard.components.report_view import render_report_view
from dashboard.components.result_panel import render_result_panel
from dashboard.components.visualizer import render_visual_inspection
from dashboard.utils.classification_presentation import (
    CLASSIFICATION_PRESENTATION,
    get_classification_presentation,
)
from dashboard.utils.pipeline_runner import run_inspection_pipeline


class TestDashboardPagesArchitecture(unittest.TestCase):
    def test_navigation_pages_definition(self):
        """Verify the exact 6 pages are defined in order."""
        expected_pages = [
            "New Inspection",
            "Inspection Result",
            "Visual Inspection",
            "Measurements & Findings",
            "Inspection Report",
            "Architecture",
        ]
        self.assertEqual(NAV_PAGES, expected_pages)
        for page in expected_pages:
            self.assertIn(page, PAGE_LABELS)
            self.assertTrue(len(PAGE_LABELS[page]) > 0)

    def test_page_components_import_and_callable(self):
        """Verify each page component is callable."""
        self.assertTrue(callable(render_new_inspection_page))
        self.assertTrue(callable(render_result_panel))
        self.assertTrue(callable(render_visual_inspection))
        self.assertTrue(callable(render_measurements_page))
        self.assertTrue(callable(render_report_view))
        self.assertTrue(callable(render_system_architecture))

    def test_classification_presentation_all_states(self):
        """Verify centralized presentation mapping handles all 5 required classifications."""
        states = ["OK", "SPACING DEFECT", "WELD DEFECT", "MULTIPLE DEFECTS", "REVIEW"]
        for state in states:
            pres = get_classification_presentation(state)
            self.assertIsInstance(pres, dict)
            self.assertIn("label", pres)
            self.assertIn("title", pres)
            self.assertIn("subtitle", pres)
            self.assertIn("color", pres)
            self.assertIn("icon", pres)
            self.assertIn("class_name", pres)
            self.assertEqual(pres["label"], state)

        # Check color contracts
        self.assertEqual(get_classification_presentation("OK")["color"], "#16a34a")
        self.assertEqual(get_classification_presentation("REVIEW")["color"], "#d97706")
        self.assertEqual(get_classification_presentation("SPACING DEFECT")["color"], "#dc2626")
        self.assertEqual(get_classification_presentation("WELD DEFECT")["color"], "#dc2626")
        self.assertEqual(get_classification_presentation("MULTIPLE DEFECTS")["color"], "#dc2626")

    def test_ok_display_contracts(self):
        """Verify OK presentation contract."""
        pres = get_classification_presentation("OK")
        self.assertEqual(pres["label"], "OK")
        self.assertEqual(pres["title"], "✓ OK")
        self.assertEqual(pres["subtitle"], "Inspection Passed")
        self.assertEqual(pres["color"], "#16a34a")
        self.assertEqual(pres["icon"], "✓")
        self.assertEqual(pres["class_name"], "verdict-ok")

    def test_spacing_defect_display_contracts(self):
        """Verify SPACING DEFECT presentation contract."""
        pres = get_classification_presentation("SPACING DEFECT")
        self.assertEqual(pres["label"], "SPACING DEFECT")
        self.assertEqual(pres["title"], "✕ SPACING DEFECT")
        self.assertEqual(pres["subtitle"], "Configured spacing tolerance violated")
        self.assertEqual(pres["color"], "#dc2626")
        self.assertEqual(pres["icon"], "✕")
        self.assertEqual(pres["class_name"], "verdict-fail")

    def test_weld_defect_display_contracts(self):
        """Verify WELD DEFECT presentation contract."""
        pres = get_classification_presentation("WELD DEFECT")
        self.assertEqual(pres["label"], "WELD DEFECT")
        self.assertEqual(pres["title"], "✕ WELD DEFECT")
        self.assertEqual(pres["subtitle"], "Confirmed weld/intersection defect")
        self.assertEqual(pres["color"], "#dc2626")
        self.assertEqual(pres["icon"], "✕")
        self.assertEqual(pres["class_name"], "verdict-fail")

    def test_multiple_defects_display_contracts(self):
        """Verify MULTIPLE DEFECTS presentation contract."""
        pres = get_classification_presentation("MULTIPLE DEFECTS")
        self.assertEqual(pres["label"], "MULTIPLE DEFECTS")
        self.assertEqual(pres["title"], "✕ MULTIPLE DEFECTS")
        self.assertEqual(pres["subtitle"], "More than one confirmed defect category")
        self.assertEqual(pres["color"], "#dc2626")
        self.assertEqual(pres["icon"], "✕")
        self.assertEqual(pres["class_name"], "verdict-fail")

    def test_review_display_contracts(self):
        """Verify REVIEW presentation contract."""
        pres = get_classification_presentation("REVIEW")
        self.assertEqual(pres["label"], "REVIEW")
        self.assertEqual(pres["title"], "⚠ REVIEW")
        self.assertEqual(pres["subtitle"], "Human Verification Required")
        self.assertEqual(pres["color"], "#d97706")
        self.assertEqual(pres["icon"], "⚠")
        self.assertEqual(pres["class_name"], "verdict-review")

    def test_missing_optional_result_fields_safety(self):
        """Verify dashboard data processing handles missing or None optional fields safely."""
        from dashboard.utils.export import generate_json_report, generate_text_report, generate_csv_spacings
        from dashboard.utils.pipeline_runner import PipelineInspectionResult, AnomalyItem
        from core.image_loader import ImageInfo
        from core.preprocessing import PreprocessingResult
        from core.wire_detection import WireGridDetectionResult
        from core.weld_intersection import WeldIntersectionResult
        from core.inspection_decision import InspectionDecision

        # Create sparse results with None/empty optional fields
        sparse_spacing = MeshSpacingResult(
            source_name="sparse_mesh",
            vertical_spacings=[],
            horizontal_spacings=[],
            notes="",
        )
        sparse_decision = InspectionDecision(
            source_name="sparse_mesh",
            final_status="REVIEW",
            reasons=["Evidence incomplete"],
            notes="",
        )
        sparse_wire = WireGridDetectionResult(
            source_name="sparse_mesh",
            image_width=100,
            image_height=100,
        )
        sparse_weld = WeldIntersectionResult(source_name="sparse_mesh")
        sparse_info = ImageInfo(
            path=Path("sparse.jpg"),
            width=100,
            height=100,
            channels=3,
            file_format="jpg",
            file_size_bytes=1024,
        )
        sparse_prep = PreprocessingResult(
            source_name="sparse.jpg",
            original_width=100,
            original_height=100,
            processed_width=100,
            processed_height=100,
            resize_scale=1.0,
            otsu_threshold=128.0,
            output_paths={},
        )

        sparse_result = PipelineInspectionResult(
            inspection_id="INSP-SPARSE",
            timestamp="2026-09-25 12:00:00",
            source_name="sparse.jpg",
            input_source_type="UPLOAD",
            original_image=np.zeros((100, 100, 3), dtype=np.uint8),
            image_info=sparse_info,
            preprocessing_result=sparse_prep,
            grayscale_image=np.zeros((100, 100), dtype=np.uint8),
            edge_image=np.zeros((100, 100), dtype=np.uint8),
            wire_result=sparse_wire,
            weld_result=sparse_weld,
            spacing_result=sparse_spacing,
            decision=sparse_decision,
            final_classification="REVIEW",
            anomalies=[
                AnomalyItem(
                    id=1,
                    category="Sparse Anomaly",
                    location="Location X",
                    evidence="Evidence Y",
                    status="REVIEW",
                    coordinates_px=None,  # Optional None coordinates
                )
            ],
        )

        # Export generators should execute cleanly without raising exceptions
        json_str = generate_json_report(sparse_result)
        self.assertIn("INSP-SPARSE", json_str)

        text_str = generate_text_report(sparse_result)
        self.assertIn("INSP-SPARSE", text_str)

        csv_str = generate_csv_spacings(sparse_result)
        self.assertIn("Axis,Index,Wire_1_Index", csv_str)
        self.assertIn("Pixel_Spacing_Px", csv_str)

    def test_profile_and_tolerance_unavailable_handling(self):
        """Verify behavior when product profile has no configured tolerance."""
        from core.inspection_decision import make_inspection_decision
        profile = STANDARD_PROFILES.get("P001")
        self.assertIsNotNone(profile)
        self.assertIsNone(profile.vertical_tolerance_mm)
        self.assertIsNone(profile.horizontal_tolerance_mm)

        spacing_res = MeshSpacingResult(source_name="test_mesh")
        comp = compare_against_profile(spacing_res, profile)
        self.assertEqual(comp.profile_id, "P001")

        # Verify decision engine marks tolerance as NO_TOLERANCE_CONFIGURED
        decision = make_inspection_decision(
            spacing_result=spacing_res,
            profile=profile,
            source_name="test_mesh",
        )
        self.assertEqual(decision.configured_tolerance_status, "NO_TOLERANCE_CONFIGURED")
        self.assertIn("no validated tolerance configured", " ".join(decision.reasons))

    def test_no_runtime_crash_from_mesh_spacing_result(self):
        """Verify MeshSpacingResult has no profile_comparison attribute and safe pattern works."""
        spacing_res = MeshSpacingResult(source_name="test_mesh")
        
        # Verify absence of legacy attribute
        self.assertFalse(hasattr(spacing_res, "profile_comparison"))
        self.assertIsNone(getattr(spacing_res, "profile_comparison", None))

        # Safe profile evaluation pattern
        profile = STANDARD_PROFILES.get("P001")
        comp = compare_against_profile(spacing_res, profile)
        self.assertIsNotNone(comp)

    def test_no_raw_exception_or_traceback_shown(self):
        """Verify text outputs do not leak Python tracebacks or raw exception strings."""
        from dashboard.utils.export import generate_text_report, generate_json_report
        img_path = DATA_INPUT_DIR / "IMG_20260920_200712.jpg"
        img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        result = run_inspection_pipeline(
            image_input=img,
            source_name=img_path.name,
            input_source_type="UPLOAD",
        )

        text_out = generate_text_report(result)
        self.assertNotIn("Traceback (most recent call last)", text_out)
        self.assertNotIn("AttributeError", text_out)
        self.assertNotIn("TypeError", text_out)
        self.assertNotIn("<object at", text_out)

    def test_real_validation_image_produces_legitimate_review(self):
        """Verify real validation image IMG_20260920_200712.jpg produces legitimate REVIEW."""
        img_path = DATA_INPUT_DIR / "IMG_20260920_200712.jpg"
        self.assertTrue(img_path.exists(), f"Validation image not found at {img_path}")

        img = cv2.imread(str(img_path), cv2.IMREAD_UNCHANGED)
        self.assertIsNotNone(img)

        result = run_inspection_pipeline(
            image_input=img,
            source_name=img_path.name,
            input_source_type="UPLOAD",
        )

        self.assertEqual(result.final_classification, "REVIEW")
        self.assertEqual(result.wire_result.num_horizontal_wires, 5)
        self.assertEqual(result.wire_result.num_vertical_wires, 4)
        self.assertEqual(result.wire_result.num_intersections, 18)
        self.assertEqual(result.wire_result.expected_intersections, 20)
        self.assertEqual(result.weld_result.num_normal, 10)
        self.assertEqual(result.weld_result.num_potentially_anomalous, 8)
        self.assertAlmostEqual(result.spacing_result.mean_vertical_spacing_px, 270.0, places=1)
        self.assertAlmostEqual(result.spacing_result.mean_horizontal_spacing_px, 280.5, places=1)
        self.assertAlmostEqual(result.spacing_result.mean_vertical_spacing_mm, 24.55, places=1)
        self.assertIn("18/20 expected intersections detected", " ".join(result.decision.reasons))


if __name__ == "__main__":
    unittest.main()
