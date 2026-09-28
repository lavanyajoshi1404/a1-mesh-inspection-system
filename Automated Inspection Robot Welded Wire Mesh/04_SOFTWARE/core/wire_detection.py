"""
Milestone 4 - wire/grid detection.

Detects horizontal and vertical wires and their intersections from a
preprocessed edge image (the output of core.preprocessing's Canny
step), and reports pixel-space detection-quality metrics.

Explicitly OUT of scope here:
  - No spacing measurement in mm (that needs calibration applied on
    purpose, and is its own milestone - this module works in pixel
    space only).
  - No PASS/FAIL, tolerance, or defect decision of any kind.
  - No claim about which physical sample this is or what product it
    belongs to.

Pipeline position: this module takes an EDGE IMAGE (as produced by
core.preprocessing.preprocess_image) as input, not a raw or grayscale
image - keeping wire detection independent of preprocessing exactly as
the project architecture requires. It does not call core.preprocessing
itself; the caller is responsible for producing the edge image first.

Algorithm: cv2.HoughLinesP to find straight line segments in the edge
image, classified as horizontal/vertical by angle (segments at other
angles are discarded as noise), then 1D-clustered by position (y for
horizontal, x for vertical) to merge a single physical wire's multiple
edge fragments (its two long edges, and/or broken sub-segments from a
slightly bowed wire) into one reported wire position. Intersections are
estimated by checking, for each horizontal/vertical wire pair, whether
their detected pixel extents actually overlap near the candidate
crossing point - not simply every pairwise combination.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np

from config.settings import (
    WIRE_ANGLE_TOLERANCE_DEG,
    WIRE_CLUSTER_DISTANCE_PX,
    WIRE_HOUGH_MAX_LINE_GAP_PX,
    WIRE_HOUGH_MIN_LINE_LENGTH_PX,
    WIRE_HOUGH_RHO,
    WIRE_HOUGH_THETA_DEG,
    WIRE_HOUGH_THRESHOLD,
    WIRE_INTERSECTION_TOLERANCE_PX,
)


class WireDetectionError(Exception):
    """Raised when wire detection cannot be attempted at all (bad input),
    as distinct from attempting it and finding few/no wires."""


@dataclass
class DetectedWire:
    """One detected physical wire (horizontal or vertical), merged from
    possibly several raw line-segment detections of its edges/fragments.

    position_px: the wire's representative coordinate - y for a
        horizontal wire, x for a vertical wire (median of contributing
        segment midpoints, robust to a stray fragment).
    extent_px: (min, max) pixel range the wire was actually observed
        across, along its own length (x-range for horizontal, y-range
        for vertical) - used for the intersection overlap check, and
        reported so a caller can see how much of the frame this wire
        was actually detected in versus assumed.
    segment_count: how many raw Hough segments were merged into this
        one wire - a rough per-wire detection-confidence indicator.
    """
    position_px: float
    extent_px: Tuple[float, float]
    segment_count: int


@dataclass
class Intersection:
    """One estimated wire-crossing point, in pixel coordinates."""
    x_px: float
    y_px: float
    horizontal_wire_index: int
    vertical_wire_index: int


@dataclass
class WireGridDetectionResult:
    """Structured, factual record of what was detected. Holds pixel-
    space geometry and detection-quality metrics only - no labels, no
    physical measurements, no pass/fail verdict.
    """
    source_name: str
    image_width: int
    image_height: int
    horizontal_wires: List[DetectedWire] = field(default_factory=list)
    vertical_wires: List[DetectedWire] = field(default_factory=list)
    intersections: List[Intersection] = field(default_factory=list)
    raw_segments_total: int = 0
    raw_segments_horizontal: int = 0
    raw_segments_vertical: int = 0
    raw_segments_discarded_angle: int = 0
    mean_horizontal_angle_deviation_deg: float = 0.0
    mean_vertical_angle_deviation_deg: float = 0.0

    @property
    def num_horizontal_wires(self) -> int:
        return len(self.horizontal_wires)

    @property
    def num_vertical_wires(self) -> int:
        return len(self.vertical_wires)

    @property
    def num_intersections(self) -> int:
        return len(self.intersections)

    @property
    def expected_intersections(self) -> int:
        """Grid-assumption intersection count if every horizontal wire
        crossed every vertical wire. Compared against num_intersections
        as a completeness indicator - it does NOT mean the grid is
        assumed regular; it's just the maximum possible count."""
        return self.num_horizontal_wires * self.num_vertical_wires

    @property
    def intersection_completeness(self) -> float:
        """num_intersections / expected_intersections, or 0.0 if no
        wires were detected on one axis. A quality/coverage metric, not
        a spacing or alignment measurement."""
        expected = self.expected_intersections
        return (self.num_intersections / expected) if expected > 0 else 0.0


def _cluster_1d(positions: List[float], max_gap: float) -> List[List[int]]:
    """Group indices of `positions` into clusters where consecutive
    sorted values are within `max_gap` of each other. Returns a list of
    index-lists (into the original `positions` array), one per cluster.
    """
    if not positions:
        return []
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    clusters: List[List[int]] = [[order[0]]]
    for idx in order[1:]:
        if positions[idx] - positions[clusters[-1][-1]] <= max_gap:
            clusters[-1].append(idx)
        else:
            clusters.append([idx])
    return clusters


def detect_wire_grid(edges: np.ndarray, source_name: str) -> WireGridDetectionResult:
    """Detect horizontal/vertical wires and their intersections from a
    preprocessed edge image.

    Args:
        edges: Single-channel edge image (e.g. the Canny output from
            core.preprocessing.preprocess_image). Not a raw or color
            image - pass the edge map specifically.
        source_name: Name for reporting (e.g. the source filename).

    Returns:
        A WireGridDetectionResult. Empty wire/intersection lists are a
        valid result (nothing detected), not an error - only a genuinely
        invalid input raises.

    Raises:
        WireDetectionError: for invalid input (empty array, wrong
            number of dimensions).
    """
    if edges is None or not isinstance(edges, np.ndarray) or edges.size == 0:
        raise WireDetectionError("detect_wire_grid received an empty or invalid edge image.")
    if edges.ndim != 2:
        raise WireDetectionError(
            f"detect_wire_grid expects a single-channel edge image, got shape {edges.shape}. "
            f"Pass the edge output of core.preprocessing, not a color image."
        )

    height, width = edges.shape[:2]

    raw_lines = cv2.HoughLinesP(
        edges,
        rho=WIRE_HOUGH_RHO,
        theta=np.deg2rad(WIRE_HOUGH_THETA_DEG),
        threshold=WIRE_HOUGH_THRESHOLD,
        minLineLength=WIRE_HOUGH_MIN_LINE_LENGTH_PX,
        maxLineGap=WIRE_HOUGH_MAX_LINE_GAP_PX,
    )

    result = WireGridDetectionResult(source_name=source_name, image_width=width, image_height=height)

    if raw_lines is None:
        return result  # valid: just nothing detected

    result.raw_segments_total = len(raw_lines)

    h_positions: List[float] = []   # y-center of each horizontal segment
    h_extents: List[Tuple[float, float]] = []  # (x_min, x_max) of that segment
    h_angle_devs: List[float] = []

    v_positions: List[float] = []   # x-center of each vertical segment
    v_extents: List[Tuple[float, float]] = []  # (y_min, y_max) of that segment
    v_angle_devs: List[float] = []

    for line in raw_lines[:, 0]:
        x1, y1, x2, y2 = [float(v) for v in line]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Normalize to [0, 180) so 0 and 180 (both "horizontal") match,
        # and -90/90 (both "vertical") match.
        norm_angle = angle % 180

        horizontal_dev = min(norm_angle, 180 - norm_angle)  # distance to 0/180
        vertical_dev = abs(norm_angle - 90)                  # distance to 90

        if horizontal_dev <= WIRE_ANGLE_TOLERANCE_DEG:
            h_positions.append((y1 + y2) / 2)
            h_extents.append((min(x1, x2), max(x1, x2)))
            h_angle_devs.append(horizontal_dev)
        elif vertical_dev <= WIRE_ANGLE_TOLERANCE_DEG:
            v_positions.append((x1 + x2) / 2)
            v_extents.append((min(y1, y2), max(y1, y2)))
            v_angle_devs.append(vertical_dev)
        else:
            result.raw_segments_discarded_angle += 1

    result.raw_segments_horizontal = len(h_positions)
    result.raw_segments_vertical = len(v_positions)
    result.mean_horizontal_angle_deviation_deg = (
        round(float(np.mean(h_angle_devs)), 3) if h_angle_devs else 0.0
    )
    result.mean_vertical_angle_deviation_deg = (
        round(float(np.mean(v_angle_devs)), 3) if v_angle_devs else 0.0
    )

    for cluster in _cluster_1d(h_positions, WIRE_CLUSTER_DISTANCE_PX):
        positions = [h_positions[i] for i in cluster]
        x_mins = [h_extents[i][0] for i in cluster]
        x_maxs = [h_extents[i][1] for i in cluster]
        result.horizontal_wires.append(DetectedWire(
            position_px=round(float(np.median(positions)), 2),
            extent_px=(round(min(x_mins), 2), round(max(x_maxs), 2)),
            segment_count=len(cluster),
        ))
    result.horizontal_wires.sort(key=lambda w: w.position_px)

    for cluster in _cluster_1d(v_positions, WIRE_CLUSTER_DISTANCE_PX):
        positions = [v_positions[i] for i in cluster]
        y_mins = [v_extents[i][0] for i in cluster]
        y_maxs = [v_extents[i][1] for i in cluster]
        result.vertical_wires.append(DetectedWire(
            position_px=round(float(np.median(positions)), 2),
            extent_px=(round(min(y_mins), 2), round(max(y_maxs), 2)),
            segment_count=len(cluster),
        ))
    result.vertical_wires.sort(key=lambda w: w.position_px)

    for hi, hw in enumerate(result.horizontal_wires):
        for vi, vw in enumerate(result.vertical_wires):
            x_ok = (vw.position_px >= hw.extent_px[0] - WIRE_INTERSECTION_TOLERANCE_PX and
                    vw.position_px <= hw.extent_px[1] + WIRE_INTERSECTION_TOLERANCE_PX)
            y_ok = (hw.position_px >= vw.extent_px[0] - WIRE_INTERSECTION_TOLERANCE_PX and
                    hw.position_px <= vw.extent_px[1] + WIRE_INTERSECTION_TOLERANCE_PX)
            if x_ok and y_ok:
                result.intersections.append(Intersection(
                    x_px=vw.position_px, y_px=hw.position_px,
                    horizontal_wire_index=hi, vertical_wire_index=vi,
                ))

    return result


def save_wire_detection_result(result: WireGridDetectionResult, output_dir) -> "Path":
    """Save a wire detection result as JSON, following the same
    convention as core.calibration.save_calibration_result. Never
    written into 02_DATASET.
    """
    import json
    from dataclasses import asdict
    from pathlib import Path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source_name).stem
    output_path = output_dir / f"wire_detection_{stem}.json"

    payload = {
        "source_name": result.source_name,
        "image_width": result.image_width,
        "image_height": result.image_height,
        "horizontal_wires": [asdict(w) for w in result.horizontal_wires],
        "vertical_wires": [asdict(w) for w in result.vertical_wires],
        "intersections": [asdict(i) for i in result.intersections],
        "raw_segments_total": result.raw_segments_total,
        "raw_segments_horizontal": result.raw_segments_horizontal,
        "raw_segments_vertical": result.raw_segments_vertical,
        "raw_segments_discarded_angle": result.raw_segments_discarded_angle,
        "mean_horizontal_angle_deviation_deg": result.mean_horizontal_angle_deviation_deg,
        "mean_vertical_angle_deviation_deg": result.mean_vertical_angle_deviation_deg,
        "num_horizontal_wires": result.num_horizontal_wires,
        "num_vertical_wires": result.num_vertical_wires,
        "num_intersections": result.num_intersections,
        "expected_intersections": result.expected_intersections,
        "intersection_completeness": round(result.intersection_completeness, 4),
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    return output_path
