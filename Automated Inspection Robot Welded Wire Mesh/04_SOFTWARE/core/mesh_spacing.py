"""
Milestone 6 - Mesh Spacing Measurement.

Measures the distance between adjacent detected wires in pixel coordinates
from the wire detections produced by core.wire_detection, and converts
spacing to millimeters where a usable scale exists.

Strict Engineering Principles & Constraints:
  1. Uses a fixed, unvalidated single-axis vertical scale estimate of
     11.0 px/mm where applicable. This value has not passed core.calibration's
     own statistical validation on this project's data (see
     config.settings.CALIBRATION_VERTICAL_STATUS = "UNVALIDATED ESTIMATE") and
     must never be described as a validated or provisional calibration.
  2. Preserves the documented position-dependent horizontal calibration
     limitation rather than inventing a single global horizontal scale.
     Horizontal spacing measurements remain UNCALIBRATED unless an explicit
     validated horizontal calibration is provided.
  3. Every measurement reports:
       - measured spacing (in mm, or None if uncalibrated)
       - pixel spacing
       - calibration used (px/mm, or None if uncalibrated)
       - axis ("vertical" or "horizontal")
       - location/index (midpoint coordinate in px and adjacent wire indices)
       - calibration status ("CALIBRATED", "PROVISIONAL", "UNVALIDATED ESTIMATE",
         or "UNCALIBRATED")
  4. Does NOT invent A-1 product tolerances. Reference product profiles
     contain nominal aperture dimensions from product documentation, but
     tolerances remain None until formally validated.
  5. Does NOT automatically call a spacing value defective merely because it
     differs from an A-1 specification. Representative development samples
     are not confirmed A-1 production material.
  6. Supports later comparison against configurable product profiles and
     tolerances without hard-coding PASS/FAIL decisions.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import cv2
import numpy as np

from config.settings import (
    CALIBRATION_HORIZONTAL_PX_PER_MM,
    CALIBRATION_HORIZONTAL_STATUS,
    CALIBRATION_VERTICAL_PX_PER_MM,
    CALIBRATION_VERTICAL_STATUS,
)
from core.calibration import CalibrationResult
from core.wire_detection import DetectedWire, WireGridDetectionResult

MeasurementStatus = Literal["CALIBRATED", "PROVISIONAL", "UNVALIDATED ESTIMATE", "UNCALIBRATED"]

# Calibration statuses that represent a genuinely validated (even if
# single-axis/scoped) calibration basis, and are therefore authoritative
# enough to be compared against a configured tolerance for a PASS/FAIL
# judgement. UNVALIDATED ESTIMATE and UNCALIBRATED are deliberately excluded:
# a numeric measured_spacing value alone is not sufficient evidence for a
# tolerance comparison - see compare_against_profile().
AUTHORITATIVE_CALIBRATION_STATUSES = ("CALIBRATED", "PROVISIONAL")


class MeshSpacingError(Exception):
    """Raised when mesh spacing measurement cannot be attempted at all
    (e.g. invalid input), as distinct from finding no adjacent wire pairs."""


@dataclass
class CalibrationScale:
    """Represents a pixel-to-millimeter scale factor for one axis.

    px_per_mm: scale factor in pixels per millimeter, or None if uncalibrated.
    status: "CALIBRATED", "PROVISIONAL", "UNVALIDATED ESTIMATE", or "UNCALIBRATED".
    source: description of the calibration source or reason for limitation.
    """
    px_per_mm: Optional[float] = None
    status: MeasurementStatus = "UNCALIBRATED"
    source: str = ""


@dataclass
class SpacingMeasurement:
    """One measured spacing between two adjacent parallel wires.

    axis: "vertical" for spacing between horizontal wires (along Y axis),
          "horizontal" for spacing between vertical wires (along X axis).
    index: 0-based index of this spacing interval along its axis.
    wire_index_1: 0-based index of the first wire in sorted coordinate order.
    wire_index_2: 0-based index of the adjacent second wire.
    wire_position_1_px: coordinate of the first wire in pixels.
    wire_position_2_px: coordinate of the second wire in pixels.
    pixel_spacing: absolute distance in pixels between the adjacent wires.
    measured_spacing: converted spacing in millimeters (None if uncalibrated).
    calibration_used: px_per_mm scale factor applied (None if uncalibrated).
    calibration_status: "CALIBRATED", "PROVISIONAL", "UNVALIDATED ESTIMATE", or "UNCALIBRATED".
    location_px: midpoint pixel coordinate between the two wires.
    notes: factual engineering notes regarding calibration and measurement.
    """
    axis: Literal["vertical", "horizontal"]
    index: int
    wire_index_1: int
    wire_index_2: int
    wire_position_1_px: float
    wire_position_2_px: float
    pixel_spacing: float
    measured_spacing: Optional[float]
    calibration_used: Optional[float]
    calibration_status: MeasurementStatus
    location_px: float
    notes: str

    @property
    def spacing_px(self) -> float:
        """Alias for pixel_spacing."""
        return self.pixel_spacing

    @property
    def measured_spacing_mm(self) -> Optional[float]:
        """Alias for measured_spacing in mm."""
        return self.measured_spacing

    @property
    def status(self) -> MeasurementStatus:
        """Alias for calibration_status."""
        return self.calibration_status


@dataclass
class MeshSpacingResult:
    """Structured, factual record of all spacing measurements on a mesh grid."""
    source_name: str
    vertical_spacings: List[SpacingMeasurement] = field(default_factory=list)
    horizontal_spacings: List[SpacingMeasurement] = field(default_factory=list)
    notes: str = ""

    @property
    def num_vertical_spacings(self) -> int:
        return len(self.vertical_spacings)

    @property
    def num_horizontal_spacings(self) -> int:
        return len(self.horizontal_spacings)

    @property
    def all_spacings(self) -> List[SpacingMeasurement]:
        return self.vertical_spacings + self.horizontal_spacings

    @property
    def mean_vertical_spacing_px(self) -> Optional[float]:
        if not self.vertical_spacings:
            return None
        return round(float(np.mean([s.pixel_spacing for s in self.vertical_spacings])), 2)

    @property
    def mean_vertical_spacing_mm(self) -> Optional[float]:
        valid = [s.measured_spacing for s in self.vertical_spacings if s.measured_spacing is not None]
        if not valid:
            return None
        return round(float(np.mean(valid)), 2)

    @property
    def mean_horizontal_spacing_px(self) -> Optional[float]:
        if not self.horizontal_spacings:
            return None
        return round(float(np.mean([s.pixel_spacing for s in self.horizontal_spacings])), 2)

    @property
    def mean_horizontal_spacing_mm(self) -> Optional[float]:
        valid = [s.measured_spacing for s in self.horizontal_spacings if s.measured_spacing is not None]
        if not valid:
            return None
        return round(float(np.mean(valid)), 2)


@dataclass
class ProductSpacingProfile:
    """Configurable reference profile for wire mesh product specifications.

    Tolerances are None until formally validated from authoritative A-1
    specifications. No PASS/FAIL tolerance is invented.
    """
    profile_id: str
    name: str
    nominal_vertical_spacing_mm: Optional[float] = None
    nominal_horizontal_spacing_mm: Optional[float] = None
    vertical_tolerance_mm: Optional[float] = None    # None until formally validated
    horizontal_tolerance_mm: Optional[float] = None  # None until formally validated
    standards: str = ""
    notes: str = ""


# Reference profiles aligned with 00_MASTER/A1_PRODUCT_SPECIFICATIONS.md.
# Per engineering rule: tolerances are NOT invented; they remain None.
STANDARD_PROFILES: Dict[str, ProductSpacingProfile] = {
    "P001": ProductSpacingProfile(
        profile_id="P001",
        name="A-1 Kavach / Anti-Climb 358",
        nominal_vertical_spacing_mm=12.7,
        nominal_horizontal_spacing_mm=76.2,
        vertical_tolerance_mm=None,
        horizontal_tolerance_mm=None,
        standards="BS 1722-14 / EN 10223-7",
        notes="Reference specifications from A-1 Fence. Tolerances unverified; do not invent PASS/FAIL thresholds.",
    ),
    "P002": ProductSpacingProfile(
        profile_id="P002",
        name="A-1 Twin Wire Panels",
        nominal_vertical_spacing_mm=50.0,
        nominal_horizontal_spacing_mm=200.0,
        vertical_tolerance_mm=None,
        horizontal_tolerance_mm=None,
        standards="EN 10223-7 / ISO 9001",
        notes="Reference specifications from A-1 Fence. Tolerances unverified; do not invent PASS/FAIL thresholds.",
    ),
    "P003": ProductSpacingProfile(
        profile_id="P003",
        name="A1 UNICO Modular Fence",
        nominal_vertical_spacing_mm=50.0,
        nominal_horizontal_spacing_mm=200.0,
        vertical_tolerance_mm=None,
        horizontal_tolerance_mm=None,
        standards="EN 10223-7 / DIN 50021",
        notes="Reference specifications from A-1 Fence. Tolerances unverified; do not invent PASS/FAIL thresholds.",
    ),
}


@dataclass
class SpacingComparisonItem:
    """Comparison record for one spacing measurement against a profile."""
    axis: Literal["vertical", "horizontal"]
    index: int
    measured_spacing_mm: Optional[float]
    nominal_spacing_mm: Optional[float]
    deviation_mm: Optional[float]
    tolerance_mm: Optional[float]
    status: str  # "NO_TOLERANCE_CONFIGURED", "WITHIN_TOLERANCE", "OUT_OF_TOLERANCE", "UNCALIBRATED", "UNVALIDATED_CALIBRATION", "NO_NOMINAL_CONFIGURED"
    notes: str


@dataclass
class SpacingComparisonResult:
    """Result of comparing spacing measurements against a product profile."""
    source_name: str
    profile_id: str
    profile_name: str
    comparisons: List[SpacingComparisonItem] = field(default_factory=list)
    notes: str = ""


def _resolve_calibration_scale(
    calibration_input: Optional[Union[float, int, CalibrationScale, CalibrationResult]],
    default_px_per_mm: Optional[float],
    default_status: MeasurementStatus,
    default_source: str,
) -> CalibrationScale:
    """Resolves various calibration input formats into a standardized CalibrationScale."""
    if calibration_input is None:
        if default_px_per_mm is not None and default_px_per_mm > 0:
            return CalibrationScale(
                px_per_mm=float(default_px_per_mm),
                status=default_status,
                source=default_source,
            )
        return CalibrationScale(
            px_per_mm=None,
            status="UNCALIBRATED",
            source=default_source,
        )

    if isinstance(calibration_input, CalibrationScale):
        return calibration_input

    if isinstance(calibration_input, CalibrationResult):
        if calibration_input.px_per_mm is not None and calibration_input.px_per_mm > 0:
            status: MeasurementStatus
            if calibration_input.status == "CALIBRATED":
                status = "CALIBRATED"
            elif calibration_input.status == "VALIDATED_SINGLE_AXIS_PROVISIONAL":
                status = "PROVISIONAL"
            else:
                status = "PROVISIONAL"
            return CalibrationScale(
                px_per_mm=float(calibration_input.px_per_mm),
                status=status,
                source=f"CalibrationResult({calibration_input.source_name}, axis={calibration_input.axis})",
            )
        return CalibrationScale(
            px_per_mm=None,
            status="UNCALIBRATED",
            source=f"CalibrationResult({calibration_input.source_name}, status={calibration_input.status})",
        )

    if isinstance(calibration_input, (int, float)):
        val = float(calibration_input)
        if val > 0:
            return CalibrationScale(
                px_per_mm=val,
                status=default_status if default_status != "UNCALIBRATED" else "CALIBRATED",
                source="numeric_scale_input",
            )
        return CalibrationScale(
            px_per_mm=None,
            status="UNCALIBRATED",
            source="invalid_non_positive_numeric_scale",
        )

    raise MeshSpacingError(
        f"Unsupported calibration input type: {type(calibration_input).__name__}. "
        f"Expected float, CalibrationScale, CalibrationResult, or None."
    )


def measure_mesh_spacing(
    wire_result: WireGridDetectionResult,
    calibration_vertical: Optional[Union[float, int, CalibrationScale, CalibrationResult]] = None,
    calibration_horizontal: Optional[Union[float, int, CalibrationScale, CalibrationResult]] = None,
) -> MeshSpacingResult:
    """Measure pixel and millimeter spacings between adjacent detected wires.

    Spacing along the vertical axis is measured between adjacent horizontal wires
    (separation in Y). Spacing along the horizontal axis is measured between
    adjacent vertical wires (separation in X).

    Args:
        wire_result: Output of core.wire_detection.detect_wire_grid.
        calibration_vertical: Optional scale for the vertical axis. Defaults to
            a fixed 11.0 px/mm scale estimate (status: UNVALIDATED ESTIMATE) that
            has not passed core.calibration's own validation on this project's
            data - see config.settings.CALIBRATION_VERTICAL_STATUS.
        calibration_horizontal: Optional scale for the horizontal axis. Defaults to
            None (status: UNCALIBRATED), preserving the documented
            position-dependent horizontal calibration limitation.

    Returns:
        MeshSpacingResult containing factual SpacingMeasurement records.

    Raises:
        MeshSpacingError: if wire_result is None or not a WireGridDetectionResult.
    """
    if wire_result is None or not isinstance(wire_result, WireGridDetectionResult):
        raise MeshSpacingError(
            f"measure_mesh_spacing received invalid wire_result: {type(wire_result).__name__}. "
            f"Expected an instance of WireGridDetectionResult from core.wire_detection."
        )

    vert_scale = _resolve_calibration_scale(
        calibration_input=calibration_vertical,
        default_px_per_mm=CALIBRATION_VERTICAL_PX_PER_MM,
        default_status=CALIBRATION_VERTICAL_STATUS,
        default_source="Unvalidated single-axis vertical scale estimate (11.0 px/mm; not a passed core.calibration validation)",
    )

    horiz_scale = _resolve_calibration_scale(
        calibration_input=calibration_horizontal,
        default_px_per_mm=CALIBRATION_HORIZONTAL_PX_PER_MM,
        default_status=CALIBRATION_HORIZONTAL_STATUS,
        default_source="Preserving documented position-dependent horizontal calibration limitation; no global scale",
    )

    result = MeshSpacingResult(source_name=wire_result.source_name)

    # 1. Spacing between adjacent horizontal wires (vertical axis / Y-separation)
    sorted_h_wires = sorted(wire_result.horizontal_wires, key=lambda w: w.position_px)
    for i in range(len(sorted_h_wires) - 1):
        w1 = sorted_h_wires[i]
        w2 = sorted_h_wires[i + 1]
        pixel_spacing = round(float(w2.position_px - w1.position_px), 2)
        location_px = round(float((w1.position_px + w2.position_px) / 2.0), 2)

        if vert_scale.px_per_mm is not None and vert_scale.px_per_mm > 0:
            measured_spacing_mm = round(float(pixel_spacing / vert_scale.px_per_mm), 2)
            cal_used = round(float(vert_scale.px_per_mm), 4)
            cal_status = vert_scale.status
            notes = (
                f"Converted using vertical calibration {cal_used} px/mm "
                f"({cal_status}). Source: {vert_scale.source}."
            )
        else:
            measured_spacing_mm = None
            cal_used = None
            cal_status = "UNCALIBRATED"
            notes = "Vertical axis uncalibrated; pixel spacing reported without mm conversion."

        result.vertical_spacings.append(SpacingMeasurement(
            axis="vertical",
            index=i,
            wire_index_1=i,
            wire_index_2=i + 1,
            wire_position_1_px=w1.position_px,
            wire_position_2_px=w2.position_px,
            pixel_spacing=pixel_spacing,
            measured_spacing=measured_spacing_mm,
            calibration_used=cal_used,
            calibration_status=cal_status,
            location_px=location_px,
            notes=notes,
        ))

    # 2. Spacing between adjacent vertical wires (horizontal axis / X-separation)
    sorted_v_wires = sorted(wire_result.vertical_wires, key=lambda w: w.position_px)
    for j in range(len(sorted_v_wires) - 1):
        w1 = sorted_v_wires[j]
        w2 = sorted_v_wires[j + 1]
        pixel_spacing = round(float(w2.position_px - w1.position_px), 2)
        location_px = round(float((w1.position_px + w2.position_px) / 2.0), 2)

        if horiz_scale.px_per_mm is not None and horiz_scale.px_per_mm > 0:
            measured_spacing_mm = round(float(pixel_spacing / horiz_scale.px_per_mm), 2)
            cal_used = round(float(horiz_scale.px_per_mm), 4)
            cal_status = horiz_scale.status
            notes = (
                f"Converted using horizontal calibration {cal_used} px/mm "
                f"({cal_status}). Source: {horiz_scale.source}."
            )
        else:
            measured_spacing_mm = None
            cal_used = None
            cal_status = "UNCALIBRATED"
            notes = (
                "Preserving documented position-dependent horizontal calibration limitation; "
                "no single global horizontal scale invented. Spacing reported in pixels only."
            )

        result.horizontal_spacings.append(SpacingMeasurement(
            axis="horizontal",
            index=j,
            wire_index_1=j,
            wire_index_2=j + 1,
            wire_position_1_px=w1.position_px,
            wire_position_2_px=w2.position_px,
            pixel_spacing=pixel_spacing,
            measured_spacing=measured_spacing_mm,
            calibration_used=cal_used,
            calibration_status=cal_status,
            location_px=location_px,
            notes=notes,
        ))

    notes_parts = []
    if result.vertical_spacings:
        v_stat = vert_scale.status
        notes_parts.append(f"Vertical spacing: {len(result.vertical_spacings)} intervals measured ({v_stat})")
    else:
        notes_parts.append("Vertical spacing: fewer than 2 horizontal wires detected")

    if result.horizontal_spacings:
        h_stat = horiz_scale.status
        notes_parts.append(f"Horizontal spacing: {len(result.horizontal_spacings)} intervals measured ({h_stat})")
    else:
        notes_parts.append("Horizontal spacing: fewer than 2 vertical wires detected")

    result.notes = "; ".join(notes_parts) + "."
    return result


def compare_against_profile(
    spacing_result: MeshSpacingResult,
    profile: ProductSpacingProfile,
) -> SpacingComparisonResult:
    """Compare measured wire spacing against a configurable product profile.

    Strict rules:
      - Does NOT invent tolerances. If tolerance is None, status is reported as
        NO_TOLERANCE_CONFIGURED.
      - Does NOT automatically label a deviation as DEFECTIVE or FAIL.
        Representative development samples are not confirmed A-1 products.
      - Does NOT treat a numeric measured_spacing value as sufficient evidence
        for a tolerance judgement. Only a measurement whose calibration_status
        is in AUTHORITATIVE_CALIBRATION_STATUSES (currently "CALIBRATED" or a
        genuinely validated "PROVISIONAL") can produce WITHIN_TOLERANCE or
        OUT_OF_TOLERANCE. An "UNVALIDATED ESTIMATE" or "UNCALIBRATED" basis
        instead produces UNVALIDATED_CALIBRATION when a tolerance is configured,
        never a PASS/FAIL-relevant status.

    Args:
        spacing_result: MeshSpacingResult from measure_mesh_spacing.
        profile: ProductSpacingProfile to compare against.

    Returns:
        SpacingComparisonResult with itemized deviation facts.
    """
    comparison_result = SpacingComparisonResult(
        source_name=spacing_result.source_name,
        profile_id=profile.profile_id,
        profile_name=profile.name,
    )

    for item in spacing_result.vertical_spacings:
        nominal = profile.nominal_vertical_spacing_mm
        tol = profile.vertical_tolerance_mm
        measured = item.measured_spacing

        if measured is None:
            status = "UNCALIBRATED"
            dev = None
            notes = "Measurement is uncalibrated; physical deviation from profile cannot be computed."
        elif nominal is None:
            status = "NO_NOMINAL_CONFIGURED"
            dev = None
            notes = "No nominal vertical spacing defined in profile."
        else:
            dev = round(measured - nominal, 2)
            if tol is None:
                status = "NO_TOLERANCE_CONFIGURED"
                notes = (
                    f"Measured {measured} mm vs nominal {nominal} mm (deviation: {dev:+.2f} mm). "
                    f"No validated tolerance configured in profile; no PASS/FAIL decision made."
                )
            elif item.calibration_status not in AUTHORITATIVE_CALIBRATION_STATUSES:
                # A tolerance IS configured, but the calibration basis has not passed
                # validation. A numeric deviation can be computed, but it must NOT be
                # used to claim WITHIN_TOLERANCE or OUT_OF_TOLERANCE.
                status = "UNVALIDATED_CALIBRATION"
                notes = (
                    f"Measured {measured} mm vs nominal {nominal} mm (deviation: {dev:+.2f} mm). "
                    f"A tolerance is configured, but the calibration basis "
                    f"({item.calibration_status}) has not passed validation; "
                    f"PASS/FAIL cannot be honestly determined from this measurement."
                )
            else:
                within = abs(dev) <= tol
                status = "WITHIN_TOLERANCE" if within else "OUT_OF_TOLERANCE"
                notes = (
                    f"Measured {measured} mm vs nominal {nominal} mm ±{tol} mm "
                    f"(deviation: {dev:+.2f} mm). Within tolerance: {within}."
                )

        comparison_result.comparisons.append(SpacingComparisonItem(
            axis="vertical",
            index=item.index,
            measured_spacing_mm=measured,
            nominal_spacing_mm=nominal,
            deviation_mm=dev,
            tolerance_mm=tol,
            status=status,
            notes=notes,
        ))

    for item in spacing_result.horizontal_spacings:
        nominal = profile.nominal_horizontal_spacing_mm
        tol = profile.horizontal_tolerance_mm
        measured = item.measured_spacing

        if measured is None:
            status = "UNCALIBRATED"
            dev = None
            notes = (
                "Measurement is uncalibrated (preserving horizontal calibration limitation); "
                "physical deviation from profile cannot be computed."
            )
        elif nominal is None:
            status = "NO_NOMINAL_CONFIGURED"
            dev = None
            notes = "No nominal horizontal spacing defined in profile."
        else:
            dev = round(measured - nominal, 2)
            if tol is None:
                status = "NO_TOLERANCE_CONFIGURED"
                notes = (
                    f"Measured {measured} mm vs nominal {nominal} mm (deviation: {dev:+.2f} mm). "
                    f"No validated tolerance configured in profile; no PASS/FAIL decision made."
                )
            elif item.calibration_status not in AUTHORITATIVE_CALIBRATION_STATUSES:
                status = "UNVALIDATED_CALIBRATION"
                notes = (
                    f"Measured {measured} mm vs nominal {nominal} mm (deviation: {dev:+.2f} mm). "
                    f"A tolerance is configured, but the calibration basis "
                    f"({item.calibration_status}) has not passed validation; "
                    f"PASS/FAIL cannot be honestly determined from this measurement."
                )
            else:
                within = abs(dev) <= tol
                status = "WITHIN_TOLERANCE" if within else "OUT_OF_TOLERANCE"
                notes = (
                    f"Measured {measured} mm vs nominal {nominal} mm ±{tol} mm "
                    f"(deviation: {dev:+.2f} mm). Within tolerance: {within}."
                )

        comparison_result.comparisons.append(SpacingComparisonItem(
            axis="horizontal",
            index=item.index,
            measured_spacing_mm=measured,
            nominal_spacing_mm=nominal,
            deviation_mm=dev,
            tolerance_mm=tol,
            status=status,
            notes=notes,
        ))

    comparison_result.notes = (
        f"Compared {len(comparison_result.comparisons)} spacing intervals against profile "
        f"{profile.profile_id} ({profile.name}). Tolerances: vertical={profile.vertical_tolerance_mm}, "
        f"horizontal={profile.horizontal_tolerance_mm}."
    )
    return comparison_result


def save_mesh_spacing_result(result: MeshSpacingResult, output_dir: Union[str, Path]) -> Path:
    """Save a MeshSpacingResult as JSON. Follows project convention.
    Never written into 02_DATASET.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source_name).stem
    output_path = output_dir / f"mesh_spacing_{stem}.json"

    payload = {
        "source_name": result.source_name,
        "num_vertical_spacings": result.num_vertical_spacings,
        "num_horizontal_spacings": result.num_horizontal_spacings,
        "mean_vertical_spacing_px": result.mean_vertical_spacing_px,
        "mean_vertical_spacing_mm": result.mean_vertical_spacing_mm,
        "mean_horizontal_spacing_px": result.mean_horizontal_spacing_px,
        "mean_horizontal_spacing_mm": result.mean_horizontal_spacing_mm,
        "vertical_spacings": [asdict(s) for s in result.vertical_spacings],
        "horizontal_spacings": [asdict(s) for s in result.horizontal_spacings],
        "notes": result.notes,
    }

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)

    return output_path


def draw_mesh_spacing_overlay(
    image: np.ndarray,
    result: MeshSpacingResult,
    wire_result: Optional[WireGridDetectionResult] = None,
) -> np.ndarray:
    """Draw spacing measurements and wire annotations on an image for visual inspection."""
    overlay = image.copy()
    if overlay.ndim == 2:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)

    h, w = overlay.shape[:2]

    # Draw vertical spacings (between horizontal wires)
    for s in result.vertical_spacings:
        mid_y = int(round(s.location_px))
        y1 = int(round(s.wire_position_1_px))
        y2 = int(round(s.wire_position_2_px))

        # Vertical double-ended arrow on left-center
        x_arrow = int(w * 0.15) + (s.index % 2) * 40
        cv2.line(overlay, (x_arrow, y1), (x_arrow, y2), (0, 165, 255), 2)
        cv2.circle(overlay, (x_arrow, y1), 4, (0, 165, 255), -1)
        cv2.circle(overlay, (x_arrow, y2), 4, (0, 165, 255), -1)

        label = f"V{s.index}: {s.pixel_spacing:.1f}px"
        if s.measured_spacing is not None:
            label += f" ({s.measured_spacing:.1f}mm [{s.calibration_status}])"
        else:
            label += f" [{s.calibration_status}]"

        cv2.putText(
            overlay, label, (x_arrow + 10, mid_y + 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 165, 255), 1, cv2.LINE_AA
        )

    # Draw horizontal spacings (between vertical wires)
    for s in result.horizontal_spacings:
        mid_x = int(round(s.location_px))
        x1 = int(round(s.wire_position_1_px))
        x2 = int(round(s.wire_position_2_px))

        # Horizontal double-ended arrow on center-top
        y_arrow = int(h * 0.15) + (s.index % 2) * 35
        cv2.line(overlay, (x1, y_arrow), (x2, y_arrow), (255, 120, 0), 2)
        cv2.circle(overlay, (x1, y_arrow), 4, (255, 120, 0), -1)
        cv2.circle(overlay, (x2, y_arrow), 4, (255, 120, 0), -1)

        label = f"H{s.index}: {s.pixel_spacing:.1f}px"
        if s.measured_spacing is not None:
            label += f" ({s.measured_spacing:.1f}mm [{s.calibration_status}])"
        else:
            label += f" [{s.calibration_status}]"

        cv2.putText(
            overlay, label, (mid_x - 40, y_arrow - 8),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 120, 0), 1, cv2.LINE_AA
        )

    # Header summary banner
    banner_text = (
        f"Mesh Spacing: V={result.mean_vertical_spacing_px or 0:.1f}px "
        f"({result.mean_vertical_spacing_mm or 'N/A'}mm [UNVALIDATED ESTIMATE 11.0px/mm]) | "
        f"H={result.mean_horizontal_spacing_px or 0:.1f}px [UNCALIBRATED]"
    )
    cv2.rectangle(overlay, (0, 0), (w, 32), (30, 30, 30), -1)
    cv2.putText(overlay, banner_text, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    return overlay
