"""
Milestone 4 tests for core.wire_detection.

Uses a synthetic grid image (known number of horizontal/vertical wires,
known positions) built with cv2 + Canny, so expected counts are known
ground truth rather than eyeballed from a real photo. The real-image
run against the actual dataset is done separately and reported in the
milestone writeup, not here.

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

from core.wire_detection import WireDetectionError, detect_wire_grid


def _make_synthetic_grid_edges(width=600, height=800, h_lines=5, v_lines=4, thickness=6):
    """A clean synthetic wire-mesh-like grid, run through the same
    Canny step Milestone 2 uses, so this exercises the real edge
    characteristics (double edges per wire) wire_detection must handle.
    """
    img = np.full((height, width, 3), 200, dtype=np.uint8)
    h_ys = np.linspace(80, height - 80, h_lines).astype(int)
    v_xs = np.linspace(80, width - 80, v_lines).astype(int)
    for y in h_ys:
        cv2.line(img, (40, int(y)), (width - 40, int(y)), (60, 60, 60), thickness)
    for x in v_xs:
        cv2.line(img, (int(x), 40), (int(x), height - 40), (60, 60, 60), thickness)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return edges, h_ys, v_xs


class TestWireDetection(unittest.TestCase):
    def test_synthetic_grid_detects_correct_wire_counts(self):
        edges, h_ys, v_xs = _make_synthetic_grid_edges(h_lines=5, v_lines=4)
        result = detect_wire_grid(edges, "synthetic_grid.jpg")
        self.assertEqual(result.num_horizontal_wires, 5)
        self.assertEqual(result.num_vertical_wires, 4)

    def test_synthetic_grid_wire_positions_are_accurate(self):
        edges, h_ys, v_xs = _make_synthetic_grid_edges(h_lines=5, v_lines=4)
        result = detect_wire_grid(edges, "synthetic_grid.jpg")
        detected_y = [w.position_px for w in result.horizontal_wires]
        for expected, actual in zip(sorted(h_ys), detected_y):
            self.assertAlmostEqual(expected, actual, delta=5.0)
        detected_x = [w.position_px for w in result.vertical_wires]
        for expected, actual in zip(sorted(v_xs), detected_x):
            self.assertAlmostEqual(expected, actual, delta=5.0)

    def test_synthetic_grid_intersection_count_matches_grid(self):
        edges, h_ys, v_xs = _make_synthetic_grid_edges(h_lines=5, v_lines=4)
        result = detect_wire_grid(edges, "synthetic_grid.jpg")
        # A full 5x4 grid should show every horizontal wire crossing
        # every vertical wire within the drawn extents.
        self.assertEqual(result.num_intersections, 5 * 4)
        self.assertEqual(result.expected_intersections, 20)
        self.assertAlmostEqual(result.intersection_completeness, 1.0, delta=0.01)

    def test_blank_edge_image_detects_nothing_without_error(self):
        blank = np.zeros((400, 400), dtype=np.uint8)
        result = detect_wire_grid(blank, "blank.jpg")
        self.assertEqual(result.num_horizontal_wires, 0)
        self.assertEqual(result.num_vertical_wires, 0)
        self.assertEqual(result.num_intersections, 0)

    def test_empty_array_raises(self):
        with self.assertRaises(WireDetectionError):
            detect_wire_grid(np.array([]), "empty.jpg")

    def test_none_input_raises(self):
        with self.assertRaises(WireDetectionError):
            detect_wire_grid(None, "missing.jpg")

    def test_color_image_input_raises(self):
        color = np.zeros((400, 400, 3), dtype=np.uint8)
        with self.assertRaises(WireDetectionError):
            detect_wire_grid(color, "color.jpg")

    def test_diagonal_lines_are_discarded_not_misclassified(self):
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        cv2.line(img, (20, 20), (380, 380), (255, 255, 255), 4)  # pure diagonal
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        result = detect_wire_grid(edges, "diagonal.jpg")
        self.assertEqual(result.num_horizontal_wires, 0)
        self.assertEqual(result.num_vertical_wires, 0)
        self.assertGreater(result.raw_segments_discarded_angle, 0)

    def test_wire_extent_reflects_actual_drawn_span(self):
        edges, h_ys, v_xs = _make_synthetic_grid_edges(width=600, h_lines=5, v_lines=4)
        result = detect_wire_grid(edges, "synthetic_grid.jpg")
        for wire in result.horizontal_wires:
            self.assertGreater(wire.extent_px[1] - wire.extent_px[0], 400)  # spans most of the 520px drawn line

    def test_angle_deviation_is_near_zero_for_axis_aligned_grid(self):
        edges, _, _ = _make_synthetic_grid_edges()
        result = detect_wire_grid(edges, "synthetic_grid.jpg")
        self.assertLess(result.mean_horizontal_angle_deviation_deg, 2.0)
        self.assertLess(result.mean_vertical_angle_deviation_deg, 2.0)

    def test_sparser_grid_has_fewer_wires_and_intersections(self):
        edges, _, _ = _make_synthetic_grid_edges(h_lines=2, v_lines=2)
        result = detect_wire_grid(edges, "sparse_grid.jpg")
        self.assertEqual(result.num_horizontal_wires, 2)
        self.assertEqual(result.num_vertical_wires, 2)
        self.assertEqual(result.num_intersections, 4)


if __name__ == "__main__":
    unittest.main()
