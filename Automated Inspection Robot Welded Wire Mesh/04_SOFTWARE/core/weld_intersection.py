"""
Milestone 5 - intersection/weld-region detection.

For each wire intersection found by core.wire_detection, extracts a
small local ROI and analyzes whether the crossing's visual appearance
matches what's expected for its position in the grid (an interior
crossing should show all 4 arms continuing outward; an edge/corner
crossing should show only the arms a real panel edge would have).

STRICT SCOPE - what this module does NOT do, per project rules:
  - It does NOT assess weld strength, shear strength, penetration, or
    any other material/mechanical property. Camera images cannot
    support that claim (see PROJECT_SCOPE_AND_LIMITATIONS.md).
  - It does NOT produce a defect label. "POTENTIALLY_ANOMALOUS" is a
    visual-irregularity flag requiring human review, not a confirmed
    defect - consistent with the project's established
    OBSERVATION-HUMAN-VERIFICATION-REQUIRED convention.
  - It does NOT use ML. Classification is a deterministic, explainable
    rule based on measured pixel intensity, described below.
  - It does NOT invent thresholds: the present/absent brightness cutoff
    is the image's own Otsu threshold (recomputed per image, the same
    data-derived method core.preprocessing already uses), not a fixed
    number picked in advance.

Algorithm:
  1. For each intersection, determine its EXPECTED arms from its grid
     position (row/column index among all detected wires) - an interior
     crossing expects all 4 (up/down/left/right); a top-row crossing
     expects no "up" arm; a corner expects only 2 arms; etc. This isn't
     assumed - it follows directly from which row/column the wire is.
  2. For each of the 4 possible directions, measure the mean grayscale
     intensity of a small band just beyond the intersection center,
     along that direction. A band mean below the image's Otsu threshold
     is classified PRESENT (wire-colored); at or above it, ABSENT
     (background-colored). This rule was validated against 12 manually-
     confirmed real arm observations (3 intersections of known grid
     position x 4 directions each) with 12/12 agreement before being
     adopted - see the Milestone 5 writeup.
  3. Compare observed arms to expected arms:
       - any measurement band falling outside the image -> INSUFFICIENT_EVIDENCE
       - the intersection's own center isn't wire-colored -> INSUFFICIENT_EVIDENCE
       - observed arms == expected arms -> NORMAL
       - any mismatch (a wire that should continue doesn't, or an arm
         appears where the grid position says there shouldn't be one)
         -> POTENTIALLY_ANOMALOUS

Operates on the grayscale image from core.preprocessing (not the
threshold/binary output - that was checked against this real dataset
and found to also mark the wires' cast shadows as foreground, which
would bias a brightness-based check; the grayscale image plus a
freshly-computed Otsu split avoids that).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

import cv2
import numpy as np

from config.settings import (
    WELD_ARM_BAND_HALF_WIDTH_PX,
    WELD_ARM_INNER_MARGIN_PX,
    WELD_ARM_OUTER_RADIUS_PX,
    WELD_ROI_HALF_SIZE_PX,
)
from core.wire_detection import WireGridDetectionResult

DIRECTIONS = ("up", "down", "left", "right")


class WeldIntersectionError(Exception):
    """Raised when weld-intersection analysis cannot be attempted at all
    (bad input), as distinct from analyzing an intersection and finding
    insufficient evidence for it specifically."""


@dataclass
class IntersectionAssessment:
    """Structured, factual record for ONE intersection. Holds only
    measured facts (grid position, observed/expected arms, band
    intensities) and a status - never a defect label, weld-quality
    claim, or material property.
    """
    x_px: float
    y_px: float
    horizontal_wire_index: int
    vertical_wire_index: int
    is_top_row: bool
    is_bottom_row: bool
    is_left_column: bool
    is_right_column: bool
    expected_arms: List[str]
    observed_arms: List[str]
    arm_intensities: Dict[str, Optional[float]]  # None where out of bounds
    otsu_threshold_used: float
    status: str   # "NORMAL", "POTENTIALLY_ANOMALOUS", or "INSUFFICIENT_EVIDENCE"
    notes: str


@dataclass
class WeldIntersectionResult:
    source_name: str
    assessments: List[IntersectionAssessment] = field(default_factory=list)

    @property
    def num_analyzed(self) -> int:
        return len(self.assessments)

    @property
    def num_normal(self) -> int:
        return sum(1 for a in self.assessments if a.status == "NORMAL")

    @property
    def num_potentially_anomalous(self) -> int:
        return sum(1 for a in self.assessments if a.status == "POTENTIALLY_ANOMALOUS")

    @property
    def num_insufficient_evidence(self) -> int:
        return sum(1 for a in self.assessments if a.status == "INSUFFICIENT_EVIDENCE")


def _expected_arms(hi: int, vi: int, num_h: int, num_v: int) -> Set[str]:
    expected = set(DIRECTIONS)
    if hi == 0:
        expected.discard("up")
    if hi == num_h - 1:
        expected.discard("down")
    if vi == 0:
        expected.discard("left")
    if vi == num_v - 1:
        expected.discard("right")
    return expected


def _band_bounds(cx: int, cy: int, direction: str, height: int, width: int):
    inner, outer, band = WELD_ARM_INNER_MARGIN_PX, WELD_ARM_OUTER_RADIUS_PX, WELD_ARM_BAND_HALF_WIDTH_PX
    if direction == "up":
        y0, y1 = cy - outer, cy - inner
        x0, x1 = cx - band, cx + band
    elif direction == "down":
        y0, y1 = cy + inner, cy + outer
        x0, x1 = cx - band, cx + band
    elif direction == "left":
        x0, x1 = cx - outer, cx - inner
        y0, y1 = cy - band, cy + band
    elif direction == "right":
        x0, x1 = cx + inner, cx + outer
        y0, y1 = cy - band, cy + band
    else:
        raise WeldIntersectionError(f"Unknown direction {direction!r}")

    if x0 < 0 or y0 < 0 or x1 > width or y1 > height or x0 >= x1 or y0 >= y1:
        return None
    return x0, x1, y0, y1


def analyze_intersections(
    grayscale_image: np.ndarray,
    wire_result: WireGridDetectionResult,
) -> WeldIntersectionResult:
    """Analyze the local appearance of every intersection in wire_result.

    Args:
        grayscale_image: The grayscale image from core.preprocessing,
            at the SAME scale/coordinates wire_result was detected on
            (i.e. the same image whose edge output was passed to
            core.wire_detection.detect_wire_grid).
        wire_result: Output of core.wire_detection.detect_wire_grid.

    Returns:
        A WeldIntersectionResult with one IntersectionAssessment per
        intersection in wire_result.intersections.

    Raises:
        WeldIntersectionError: for invalid input (empty/None image, or
            wrong dimensions relative to wire_result).
    """
    if grayscale_image is None or not isinstance(grayscale_image, np.ndarray) or grayscale_image.size == 0:
        raise WeldIntersectionError("analyze_intersections received an empty or invalid image.")
    if grayscale_image.ndim != 2:
        raise WeldIntersectionError(
            f"analyze_intersections expects a single-channel grayscale image, got shape {grayscale_image.shape}."
        )
    if grayscale_image.shape != (wire_result.image_height, wire_result.image_width):
        raise WeldIntersectionError(
            f"grayscale_image shape {grayscale_image.shape} does not match wire_result's "
            f"recorded size ({wire_result.image_height}, {wire_result.image_width}) - "
            f"they must be the same image at the same scale."
        )

    height, width = grayscale_image.shape
    otsu_threshold, _ = cv2.threshold(grayscale_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    result = WeldIntersectionResult(source_name=wire_result.source_name)

    for isec in wire_result.intersections:
        cx, cy = int(round(isec.x_px)), int(round(isec.y_px))
        hi, vi = isec.horizontal_wire_index, isec.vertical_wire_index
        num_h, num_v = wire_result.num_horizontal_wires, wire_result.num_vertical_wires

        is_top = hi == 0
        is_bottom = hi == num_h - 1
        is_left = vi == 0
        is_right = vi == num_v - 1
        expected = _expected_arms(hi, vi, num_h, num_v)

        # ROI bounds check (for reporting/consistency; actual measurement
        # uses the tighter per-arm band bounds below).
        roi_half = WELD_ROI_HALF_SIZE_PX
        roi_in_bounds = (cx - roi_half >= 0 and cx + roi_half <= width and
                          cy - roi_half >= 0 and cy + roi_half <= height)

        # Center patch: is this actually wire material at all?
        center_half = WELD_ARM_INNER_MARGIN_PX
        cx0, cx1 = max(0, cx - center_half), min(width, cx + center_half)
        cy0, cy1 = max(0, cy - center_half), min(height, cy + center_half)
        center_patch = grayscale_image[cy0:cy1, cx0:cx1]
        center_intensity = float(center_patch.mean()) if center_patch.size else None

        arm_intensities: Dict[str, Optional[float]] = {}
        observed: Set[str] = set()
        any_out_of_bounds = not roi_in_bounds

        for direction in DIRECTIONS:
            bounds = _band_bounds(cx, cy, direction, height, width)
            if bounds is None:
                arm_intensities[direction] = None
                any_out_of_bounds = True
                continue
            x0, x1, y0, y1 = bounds
            band = grayscale_image[y0:y1, x0:x1]
            mean_intensity = float(band.mean())
            arm_intensities[direction] = round(mean_intensity, 2)
            if mean_intensity <= otsu_threshold:
                observed.add(direction)

        if any_out_of_bounds or center_intensity is None or center_intensity > otsu_threshold:
            status = "INSUFFICIENT_EVIDENCE"
            reasons = []
            if any_out_of_bounds:
                reasons.append("ROI/arm band extends outside image bounds")
            if center_intensity is not None and center_intensity >= otsu_threshold:
                reasons.append("intersection center is not wire-colored")
            notes = "; ".join(reasons) or "insufficient data"
        elif observed == expected:
            status = "NORMAL"
            notes = "Observed arms match the pattern expected for this grid position."
        else:
            status = "POTENTIALLY_ANOMALOUS"
            missing = sorted(expected - observed)
            unexpected = sorted(observed - expected)
            parts = []
            if missing:
                parts.append(f"expected but not observed: {missing}")
            if unexpected:
                parts.append(f"observed but not expected for this grid position: {unexpected}")
            notes = ("OBSERVATION - HUMAN VERIFICATION REQUIRED. " + "; ".join(parts) +
                     ". This flags a visual mismatch only - it is not a defect, weld-quality, "
                     "or material-property claim.")

        result.assessments.append(IntersectionAssessment(
            x_px=isec.x_px, y_px=isec.y_px,
            horizontal_wire_index=hi, vertical_wire_index=vi,
            is_top_row=is_top, is_bottom_row=is_bottom,
            is_left_column=is_left, is_right_column=is_right,
            expected_arms=sorted(expected), observed_arms=sorted(observed),
            arm_intensities=arm_intensities,
            otsu_threshold_used=round(float(otsu_threshold), 2),
            status=status, notes=notes,
        ))

    return result


def save_weld_intersection_result(result: WeldIntersectionResult, output_dir) -> "Path":
    """Save a weld-intersection result as JSON, following the same
    convention as the calibration and wire-detection savers. Never
    written into 02_DATASET.
    """
    import json
    from dataclasses import asdict
    from pathlib import Path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source_name).stem
    output_path = output_dir / f"weld_intersection_{stem}.json"

    payload = {
        "source_name": result.source_name,
        "num_analyzed": result.num_analyzed,
        "num_normal": result.num_normal,
        "num_potentially_anomalous": result.num_potentially_anomalous,
        "num_insufficient_evidence": result.num_insufficient_evidence,
        "assessments": [asdict(a) for a in result.assessments],
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    return output_path
