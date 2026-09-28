"""
Milestone 5 tests for core.weld_intersection.

Most tests build WireGridDetectionResult objects directly with known,
exact geometry - this isolates weld_intersection's own logic from
core.wire_detection's Hough-based imprecision (which is real and
already covered by its own tests in test_wire_detection.py), giving
precise, deterministic ground truth for arm-presence and grid-position
logic. One true end-to-end integration test at the bottom exercises the
real pipeline (wire_detection -> weld_intersection together) without
demanding perfect grid coverage, matching how Milestone 4's own real-
image validation accepted partial (18/20) intersection coverage rather
than requiring 100%.

Run with:
    python -m unittest discover -s tests
(from the 04_SOFTWARE/ directory)
"""

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.wire_detection import DetectedWire, Intersection, WireGridDetectionResult, detect_wire_grid
from core.weld_intersection import (
    WeldIntersectionError,
    analyze_intersections,
    save_weld_intersection_result,
)


def _make_exact_grid(width=700, height=900, h_ys=(150, 450, 750), v_xs=(150, 350, 550),
                      thickness=26, break_arm=None):
    """Render a grid with wires at EXACTLY the given positions (no Hough
    involved) and build a matching WireGridDetectionResult by hand, so
    tests can assert exact expected behavior without depending on Hough
    line-detection precision.

    break_arm: optional (h_index, v_index, direction) to erase a short
        stretch of wire immediately adjacent to that SPECIFIC
        intersection, simulating a genuine visual gap for the anomaly
        test. direction is 'up'/'down' (erase part of the vertical wire
        just above/below this intersection) or 'left'/'right' (erase
        part of the horizontal wire just left/right of it).
    """
    img = np.full((height, width), 210, dtype=np.uint8)
    x_lo, x_hi = v_xs[0], v_xs[-1]
    y_lo, y_hi = h_ys[0], h_ys[-1]

    for y in h_ys:
        cv2.line(img, (x_lo, y), (x_hi, y), 60, thickness)
    for x in v_xs:
        cv2.line(img, (x, y_lo), (x, y_hi), 60, thickness)

    if break_arm is not None:
        hi, vi, direction = break_arm
        cx, cy = v_xs[vi], h_ys[hi]
        gap = 30  # distance from the intersection center to the start of the erased stretch
        length = 25  # length of the erased stretch
        if direction == "left":
            cv2.rectangle(img, (cx - gap - length, cy - thickness), (cx - gap, cy + thickness), 210, -1)
        elif direction == "right":
            cv2.rectangle(img, (cx + gap, cy - thickness), (cx + gap + length, cy + thickness), 210, -1)
        elif direction == "up":
            cv2.rectangle(img, (cx - thickness, cy - gap - length), (cx + thickness, cy - gap), 210, -1)
        elif direction == "down":
            cv2.rectangle(img, (cx - thickness, cy + gap), (cx + thickness, cy + gap + length), 210, -1)

    gray = cv2.GaussianBlur(img, (7, 7), 0)

    wire_result = WireGridDetectionResult(source_name="exact_grid.jpg", image_width=width, image_height=height)
    for y in h_ys:
        wire_result.horizontal_wires.append(DetectedWire(
            position_px=float(y), extent_px=(float(x_lo), float(x_hi)), segment_count=1
        ))
    for x in v_xs:
        wire_result.vertical_wires.append(DetectedWire(
            position_px=float(x), extent_px=(float(y_lo), float(y_hi)), segment_count=1
        ))
    for hi, y in enumerate(h_ys):
        for vi, x in enumerate(v_xs):
            wire_result.intersections.append(Intersection(
                x_px=float(x), y_px=float(y), horizontal_wire_index=hi, vertical_wire_index=vi
            ))

    return gray, wire_result


class TestWeldIntersection(unittest.TestCase):
    def test_full_grid_all_intersections_normal(self):
        gray, wire_result = _make_exact_grid()
        result = analyze_intersections(gray, wire_result)
        self.assertEqual(result.num_analyzed, 9)
        self.assertEqual(result.num_normal, 9)
        self.assertEqual(result.num_potentially_anomalous, 0)
        self.assertEqual(result.num_insufficient_evidence, 0)

    def test_corner_intersection_has_two_expected_arms(self):
        gray, wire_result = _make_exact_grid()
        result = analyze_intersections(gray, wire_result)
        corner = next(a for a in result.assessments if a.is_top_row and a.is_left_column)
        self.assertEqual(corner.expected_arms, ["down", "right"])
        self.assertEqual(corner.observed_arms, ["down", "right"])
        self.assertEqual(corner.status, "NORMAL")

    def test_interior_intersection_expects_all_four_arms(self):
        gray, wire_result = _make_exact_grid()
        result = analyze_intersections(gray, wire_result)
        interior = next(a for a in result.assessments
                         if not a.is_top_row and not a.is_bottom_row
                         and not a.is_left_column and not a.is_right_column)
        self.assertEqual(interior.expected_arms, ["down", "left", "right", "up"])
        self.assertEqual(interior.observed_arms, ["down", "left", "right", "up"])
        self.assertEqual(interior.status, "NORMAL")

    def test_edge_intersection_has_three_expected_arms(self):
        gray, wire_result = _make_exact_grid()
        result = analyze_intersections(gray, wire_result)
        top_edge = next(a for a in result.assessments
                         if a.is_top_row and not a.is_left_column and not a.is_right_column)
        self.assertEqual(top_edge.expected_arms, ["down", "left", "right"])
        self.assertEqual(top_edge.status, "NORMAL")

    def test_broken_arm_flags_intersection_as_anomalous(self):
        # Erase the vertical wire's downward stretch just below the
        # interior intersection at (h_ys[1], v_xs[1]) = (450, 350).
        gray, wire_result = _make_exact_grid(break_arm=(1, 1, "down"))
        result = analyze_intersections(gray, wire_result)
        target = next(a for a in result.assessments
                       if a.horizontal_wire_index == 1 and a.vertical_wire_index == 1)
        self.assertEqual(target.status, "POTENTIALLY_ANOMALOUS")
        self.assertNotIn("down", target.observed_arms)
        self.assertIn("down", target.expected_arms)
        self.assertIn("HUMAN VERIFICATION REQUIRED", target.notes)

    def test_broken_arm_does_not_affect_unrelated_intersections(self):
        gray, wire_result = _make_exact_grid(break_arm=(1, 1, "down"))
        result = analyze_intersections(gray, wire_result)
        unrelated = [a for a in result.assessments
                     if not (a.horizontal_wire_index == 1 and a.vertical_wire_index == 1)]
        for a in unrelated:
            self.assertEqual(a.status, "NORMAL", f"unrelated intersection ({a.x_px},{a.y_px}) should be unaffected")

    def test_status_is_never_a_defect_or_material_claim(self):
        """Guards against accidentally overclaiming in future edits -
        status must only ever be one of the three defined values."""
        gray, wire_result = _make_exact_grid(break_arm=(1, 1, "down"))
        result = analyze_intersections(gray, wire_result)
        allowed = {"NORMAL", "POTENTIALLY_ANOMALOUS", "INSUFFICIENT_EVIDENCE"}
        for a in result.assessments:
            self.assertIn(a.status, allowed)

    def test_intersection_too_close_to_image_edge_is_insufficient_evidence(self):
        gray, wire_result = _make_exact_grid(
            width=700, height=900, h_ys=(20, 450, 750), v_xs=(150, 350, 550)
        )
        result = analyze_intersections(gray, wire_result)
        near_edge = [a for a in result.assessments if a.y_px == 20]
        for a in near_edge:
            self.assertEqual(a.status, "INSUFFICIENT_EVIDENCE")

    def test_empty_image_raises(self):
        _, wire_result = _make_exact_grid()
        with self.assertRaises(WeldIntersectionError):
            analyze_intersections(np.array([]), wire_result)

    def test_none_image_raises(self):
        _, wire_result = _make_exact_grid()
        with self.assertRaises(WeldIntersectionError):
            analyze_intersections(None, wire_result)

    def test_color_image_raises(self):
        gray, wire_result = _make_exact_grid()
        color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        with self.assertRaises(WeldIntersectionError):
            analyze_intersections(color, wire_result)

    def test_mismatched_image_size_raises(self):
        _, wire_result = _make_exact_grid(width=700, height=900)
        wrong_size_gray = np.full((400, 400), 210, dtype=np.uint8)
        with self.assertRaises(WeldIntersectionError):
            analyze_intersections(wrong_size_gray, wire_result)

    def test_no_intersections_gives_empty_result_not_error(self):
        wire_result = WireGridDetectionResult(source_name="blank.jpg", image_width=400, image_height=400)
        blank_gray = np.full((400, 400), 210, dtype=np.uint8)
        result = analyze_intersections(blank_gray, wire_result)
        self.assertEqual(result.num_analyzed, 0)

    def test_save_weld_intersection_result_writes_readable_json(self):
        import tempfile, shutil, json
        gray, wire_result = _make_exact_grid()
        result = analyze_intersections(gray, wire_result)

        tmp_dir = Path(tempfile.mkdtemp())
        try:
            path = save_weld_intersection_result(result, tmp_dir)
            self.assertTrue(path.exists())
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["num_analyzed"], result.num_analyzed)
            self.assertEqual(len(data["assessments"]), result.num_analyzed)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_end_to_end_with_real_wire_detection_pipeline(self):
        """True integration test: builds a grid image, runs the actual
        Hough-based detect_wire_grid (not hand-built geometry), then
        feeds its real output into analyze_intersections. Doesn't
        require every intersection to be found or NORMAL (Milestone 4's
        own real-image validation found 18/20, not 20/20) - just that
        the two modules work together without error and produce a
        sensible result."""
        width, height = 900, 1100
        h_ys = [150, 450, 750, 1000]
        v_xs = [150, 400, 650]
        img = np.full((height, width), 210, dtype=np.uint8)
        for y in h_ys:
            cv2.line(img, (v_xs[0], y), (v_xs[-1], y), 60, 26)
        for x in v_xs:
            cv2.line(img, (x, h_ys[0]), (x, h_ys[-1]), 60, 26)
        edges = cv2.Canny(img, 50, 150)
        gray = cv2.GaussianBlur(img, (7, 7), 0)

        wire_result = detect_wire_grid(edges, "integration_grid.jpg")
        self.assertGreater(wire_result.num_horizontal_wires, 0)
        self.assertGreater(wire_result.num_vertical_wires, 0)

        result = analyze_intersections(gray, wire_result)
        self.assertEqual(result.num_analyzed, wire_result.num_intersections)
        if result.num_analyzed > 0:
            self.assertGreater(result.num_normal + result.num_potentially_anomalous, 0)


if __name__ == "__main__":
    unittest.main()
