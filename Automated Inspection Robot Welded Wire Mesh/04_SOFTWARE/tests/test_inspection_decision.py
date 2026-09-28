"""
Tests for core.inspection_decision.

Verifies:
  1. Valid evidence with no failure condition -> PASS
  2. Provisional spacing -> REVIEW, not FAIL
  3. Uncalibrated spacing -> REVIEW
  4. Potentially anomalous intersection -> REVIEW
  5. Insufficient evidence -> REVIEW
  6. Explicit configured tolerance violation -> FAIL
  7. No configured tolerance -> must NOT produce FAIL merely from deviation
  8. Invalid / missing inputs handling
  9. Final status is always exactly one of: PASS, FAIL, REVIEW
  10. JSON serialization of inspection decision

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

# Ensure 04_SOFTWARE root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.inspection_decision import (
    InspectionDecision,
    InspectionDecisionError,
    make_inspection_decision,
    save_inspection_decision,
)
from dashboard.utils.pipeline_runner import determine_final_classification
from core.mesh_spacing import (
    STANDARD_PROFILES,
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


def _build_mock_wire_result(
    h_ys=(100.0, 300.0, 500.0),
    v_xs=(100.0, 300.0, 500.0),
    source_name="test_mesh.jpg",
) -> WireGridDetectionResult:
    """Build a complete 3x3 wire grid detection result with all 9 intersections."""
    res = WireGridDetectionResult(
        source_name=source_name,
        image_width=600,
        image_height=600,
    )
    for y in h_ys:
        res.horizontal_wires.append(
            DetectedWire(position_px=float(y), extent_px=(80.0, 520.0), segment_count=5)
        )
    for x in v_xs:
        res.vertical_wires.append(
            DetectedWire(position_px=float(x), extent_px=(80.0, 520.0), segment_count=5)
        )
    for hi, y in enumerate(h_ys):
        for vi, x in enumerate(v_xs):
            res.intersections.append(
                Intersection(
                    x_px=float(x),
                    y_px=float(y),
                    horizontal_wire_index=hi,
                    vertical_wire_index=vi,
                )
            )
    return res


def _build_mock_weld_result(
    wire_res: WireGridDetectionResult,
    anomalous_index: int = -1,
    insufficient_evidence_index: int = -1,
) -> WeldIntersectionResult:
    """Build a matching weld intersection result for wire_res."""
    res = WeldIntersectionResult(source_name=wire_res.source_name)
    for idx, isec in enumerate(wire_res.intersections):
        if idx == anomalous_index:
            status = "POTENTIALLY_ANOMALOUS"
            notes = "OBSERVATION - HUMAN VERIFICATION REQUIRED. Visual arm mismatch."
        elif idx == insufficient_evidence_index:
            status = "INSUFFICIENT_EVIDENCE"
            notes = "ROI/arm band extends outside image bounds."
        else:
            status = "NORMAL"
            notes = "Observed arms match expected pattern."

        res.assessments.append(
            IntersectionAssessment(
                x_px=isec.x_px,
                y_px=isec.y_px,
                horizontal_wire_index=isec.horizontal_wire_index,
                vertical_wire_index=isec.vertical_wire_index,
                is_top_row=(isec.horizontal_wire_index == 0),
                is_bottom_row=(isec.horizontal_wire_index == len(wire_res.horizontal_wires) - 1),
                is_left_column=(isec.vertical_wire_index == 0),
                is_right_column=(isec.vertical_wire_index == len(wire_res.vertical_wires) - 1),
                expected_arms=["up", "down", "left", "right"],
                observed_arms=["up", "down", "left", "right"] if status == "NORMAL" else [],
                arm_intensities={"up": 50.0, "down": 50.0, "left": 50.0, "right": 50.0},
                otsu_threshold_used=120.0,
                status=status,
                notes=notes,
            )
        )
    return res


def _build_mock_spacing_result(
    wire_res: WireGridDetectionResult,
    vertical_scale_status: str = "CALIBRATED",
    horizontal_scale_status: str = "CALIBRATED",
    px_per_mm: float = 10.0,
) -> MeshSpacingResult:
    """Build spacing result with configurable calibration status on each axis."""
    cal_v = CalibrationScale(
        px_per_mm=px_per_mm if vertical_scale_status != "UNCALIBRATED" else None,
        status=vertical_scale_status,
        source="mock_vertical",
    )
    cal_h = CalibrationScale(
        px_per_mm=px_per_mm if horizontal_scale_status != "UNCALIBRATED" else None,
        status=horizontal_scale_status,
        source="mock_horizontal",
    )
    return measure_mesh_spacing(wire_res, calibration_vertical=cal_v, calibration_horizontal=cal_h)


class TestInspectionDecision(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_1_valid_evidence_with_no_failure_condition_yields_pass(self):
        """When evidence is complete, fully calibrated, normal, and compliant -> PASS."""
        wire_res = _build_mock_wire_result(h_ys=(100.0, 300.0, 500.0), v_xs=(100.0, 300.0, 500.0))
        weld_res = _build_mock_weld_result(wire_res)
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED", px_per_mm=10.0)

        # Configured profile with 20.0 mm nominal and ±1.0 mm tolerance.
        # Spacing is 200 px / 10 px/mm = 20.0 mm -> exactly within tolerance.
        profile = ProductSpacingProfile(
            profile_id="P_PASS",
            name="Compliant Profile",
            nominal_vertical_spacing_mm=20.0,
            nominal_horizontal_spacing_mm=20.0,
            vertical_tolerance_mm=1.0,
            horizontal_tolerance_mm=1.0,
        )

        decision = make_inspection_decision(wire_res, weld_res, spacing_res, profile)

        self.assertEqual(decision.final_status, "PASS")
        self.assertEqual(decision.configured_tolerance_status, "WITHIN_TOLERANCE")
        self.assertEqual(decision.intersection_status, "ALL_NORMAL")
        self.assertEqual(decision.calibration_status, "CALIBRATED")

    def test_2_provisional_spacing_yields_review_not_fail(self):
        """Provisional calibration must produce REVIEW, never FAIL."""
        wire_res = _build_mock_wire_result()
        weld_res = _build_mock_weld_result(wire_res)
        # Vertical is PROVISIONAL, horizontal is CALIBRATED
        spacing_res = _build_mock_spacing_result(wire_res, "PROVISIONAL", "CALIBRATED", px_per_mm=10.0)

        decision = make_inspection_decision(wire_res, weld_res, spacing_res)

        self.assertEqual(decision.final_status, "REVIEW")
        self.assertNotEqual(decision.final_status, "FAIL")
        self.assertIn("PROVISIONAL", decision.calibration_status)
        self.assertTrue(any("provisional" in r.lower() for r in decision.reasons))

    def test_3_uncalibrated_spacing_yields_review(self):
        """Uncalibrated spacing must produce REVIEW."""
        wire_res = _build_mock_wire_result()
        weld_res = _build_mock_weld_result(wire_res)
        # Horizontal is UNCALIBRATED (as in real dataset)
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "UNCALIBRATED", px_per_mm=10.0)

        decision = make_inspection_decision(wire_res, weld_res, spacing_res)

        self.assertEqual(decision.final_status, "REVIEW")
        self.assertTrue(any("uncalibrated" in r.lower() for r in decision.reasons))

    def test_4_potentially_anomalous_intersection_yields_review(self):
        """Potentially anomalous intersection requires review; not called a weld defect."""
        wire_res = _build_mock_wire_result()
        # Mark 1 intersection as POTENTIALLY_ANOMALOUS
        weld_res = _build_mock_weld_result(wire_res, anomalous_index=4)
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED")

        decision = make_inspection_decision(wire_res, weld_res, spacing_res)

        self.assertEqual(decision.final_status, "REVIEW")
        self.assertEqual(decision.intersection_status, "ANOMALIES_DETECTED")
        self.assertTrue(any("potentially_anomalous" in r.lower() or "human verification" in r.lower() for r in decision.reasons))

    def test_5_insufficient_evidence_yields_review(self):
        """Intersection with insufficient evidence must produce REVIEW."""
        wire_res = _build_mock_wire_result()
        # Mark 1 intersection as INSUFFICIENT_EVIDENCE
        weld_res = _build_mock_weld_result(wire_res, insufficient_evidence_index=0)
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED")

        decision = make_inspection_decision(wire_res, weld_res, spacing_res)

        self.assertEqual(decision.final_status, "REVIEW")
        self.assertEqual(decision.intersection_status, "INSUFFICIENT_EVIDENCE")
        self.assertTrue(any("insufficient_evidence" in r.lower() for r in decision.reasons))

    def test_6_explicit_configured_tolerance_violation_yields_fail(self):
        """When an explicit tolerance is configured and violated -> FAIL."""
        wire_res = _build_mock_wire_result(h_ys=(100.0, 350.0))  # 250 px / 10 = 25.0 mm
        weld_res = _build_mock_weld_result(wire_res)
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED", px_per_mm=10.0)

        # Explicit tolerance: 12.7 mm ± 1.0 mm (allowed: 11.7 to 13.7 mm)
        # Measured is 25.0 mm -> clearly violates configured tolerance
        profile = ProductSpacingProfile(
            profile_id="FAIL_TEST",
            name="Strict Profile",
            nominal_vertical_spacing_mm=12.7,
            vertical_tolerance_mm=1.0,
        )

        decision = make_inspection_decision(wire_res, weld_res, spacing_res, profile)

        self.assertEqual(decision.final_status, "FAIL")
        self.assertEqual(decision.configured_tolerance_status, "TOLERANCE_VIOLATED")
        self.assertTrue(any("violates configured tolerance" in r.lower() for r in decision.reasons))

    def test_6b_unvalidated_estimate_with_tolerance_configured_cannot_fail_or_pass(self):
        """C-1 regression test: an UNVALIDATED ESTIMATE calibration basis must
        NEVER independently produce FAIL/SPACING DEFECT or a false PASS, even if
        a future developer configures a tolerance on a profile (e.g. P001) and
        the numeric deviation would otherwise violate it. This is the exact
        scenario the C-1 fix exists to prevent."""
        wire_res = _build_mock_wire_result(h_ys=(100.0, 350.0))  # 250 px
        weld_res = _build_mock_weld_result(wire_res)
        # UNVALIDATED ESTIMATE at 10.0 px/mm -> 25.0 mm measured (same numbers as
        # test_6 above, which DOES fail under a real CALIBRATED basis).
        spacing_res = _build_mock_spacing_result(
            wire_res, "UNVALIDATED ESTIMATE", "CALIBRATED", px_per_mm=10.0
        )

        # Same profile/tolerance as test_6: 12.7 mm +/- 1.0 mm. Under the pre-C-1
        # bug this would have produced FAIL/SPACING DEFECT purely from an
        # unvalidated scale.
        profile = ProductSpacingProfile(
            profile_id="FAIL_TEST",
            name="Strict Profile",
            nominal_vertical_spacing_mm=12.7,
            vertical_tolerance_mm=1.0,
        )

        decision = make_inspection_decision(wire_res, weld_res, spacing_res, profile)

        self.assertNotEqual(decision.final_status, "FAIL")
        self.assertNotEqual(decision.configured_tolerance_status, "TOLERANCE_VIOLATED")
        self.assertNotEqual(decision.configured_tolerance_status, "WITHIN_TOLERANCE")
        self.assertEqual(decision.final_status, "REVIEW")
        self.assertTrue(
            any("cannot evaluate configured tolerance" in r.lower() for r in decision.reasons)
        )

        # Also confirm this can never reach a SPACING DEFECT dashboard classification.
        classification = determine_final_classification(decision, spacing_res, weld_res)
        self.assertNotEqual(classification, "SPACING DEFECT")
        self.assertEqual(classification, "REVIEW")

    def test_7_no_configured_tolerance_does_not_produce_fail_from_deviation(self):
        """Without a configured tolerance, large deviation must NOT produce FAIL."""
        wire_res = _build_mock_wire_result(h_ys=(100.0, 350.0))  # 25.0 mm
        weld_res = _build_mock_weld_result(wire_res)
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED", px_per_mm=10.0)

        # Standard reference profile P001 has nominal 12.7 mm, but tolerance=None
        p001 = STANDARD_PROFILES["P001"]
        self.assertIsNone(p001.vertical_tolerance_mm)

        decision = make_inspection_decision(wire_res, weld_res, spacing_res, p001)

        self.assertNotEqual(decision.final_status, "FAIL")
        self.assertEqual(decision.final_status, "REVIEW")
        self.assertEqual(decision.configured_tolerance_status, "NO_TOLERANCE_CONFIGURED")

    def test_8_invalid_and_missing_inputs(self):
        """Completely invalid types raise error; partial missing evidence yields REVIEW."""
        # 1. All None raises InspectionDecisionError
        with self.assertRaises(InspectionDecisionError):
            make_inspection_decision(None, None, None)

        # 2. Invalid types raise InspectionDecisionError
        with self.assertRaises(InspectionDecisionError):
            make_inspection_decision(wire_result="not_a_wire_result")  # type: ignore

        with self.assertRaises(InspectionDecisionError):
            make_inspection_decision(weld_result="not_a_weld_result")  # type: ignore

        with self.assertRaises(InspectionDecisionError):
            make_inspection_decision(spacing_result="not_a_spacing_result")  # type: ignore

        # 3. Partial missing evidence (e.g. weld_result omitted) produces REVIEW
        wire_res = _build_mock_wire_result()
        spacing_res = _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED")
        decision = make_inspection_decision(wire_result=wire_res, spacing_result=spacing_res)

        self.assertEqual(decision.final_status, "REVIEW")
        self.assertTrue(any("weld" in r.lower() and "missing" in r.lower() for r in decision.reasons))

    def test_9_final_status_is_always_exactly_one_of_three_statuses(self):
        """The final status must strictly belong to {'PASS', 'FAIL', 'REVIEW'} across all scenarios."""
        valid_statuses = {"PASS", "FAIL", "REVIEW"}

        wire_res = _build_mock_wire_result()
        weld_res = _build_mock_weld_result(wire_res)

        scenarios = [
            # Scenario A: All calibrated, compliant profile
            _build_mock_spacing_result(wire_res, "CALIBRATED", "CALIBRATED"),
            # Scenario B: Provisional vertical
            _build_mock_spacing_result(wire_res, "PROVISIONAL", "CALIBRATED"),
            # Scenario C: Uncalibrated horizontal
            _build_mock_spacing_result(wire_res, "CALIBRATED", "UNCALIBRATED"),
            # Scenario D: Both uncalibrated
            _build_mock_spacing_result(wire_res, "UNCALIBRATED", "UNCALIBRATED"),
        ]

        for s_res in scenarios:
            dec = make_inspection_decision(wire_res, weld_res, s_res)
            self.assertIn(dec.final_status, valid_statuses)

    def test_10_save_inspection_decision_writes_readable_json(self):
        """JSON output contains all required fields and matches dataclass."""
        wire_res = _build_mock_wire_result()
        weld_res = _build_mock_weld_result(wire_res)
        spacing_res = _build_mock_spacing_result(wire_res, "PROVISIONAL", "UNCALIBRATED")

        decision = make_inspection_decision(wire_res, weld_res, spacing_res)
        out_path = save_inspection_decision(decision, self.tmp_dir)

        self.assertTrue(out_path.exists())
        with open(out_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["final_status"], decision.final_status)
        self.assertEqual(data["source_name"], decision.source_name)
        self.assertIn("reasons", data)
        self.assertIn("supporting_evidence", data)
        self.assertIn("spacing_status", data)
        self.assertIn("intersection_status", data)
        self.assertIn("calibration_status", data)
        self.assertIn("configured_tolerance_status", data)


if __name__ == "__main__":
    unittest.main()
