"""
Inspection Decision Module.

Implements the minimum viable PASS / FAIL / REVIEW decision layer for the
A1 Mesh Inspection project.

Combines the evidence already produced by:
  - core.wire_detection (grid structure, wire counts, intersection coverage)
  - core.weld_intersection (appearance analysis: NORMAL / POTENTIALLY_ANOMALOUS / INSUFFICIENT_EVIDENCE)
  - core.mesh_spacing (spacing measurements, pixel vs mm conversions)
  - core.calibration (calibration status: CALIBRATED / PROVISIONAL / UNVALIDATED ESTIMATE / UNCALIBRATED)
  - config.settings (configured product profiles & tolerances)

Strict Decision Principles:
  1. Exactly three final statuses: PASS, FAIL, REVIEW.
  2. The system is conservative: if evidence is insufficient, provisional,
     uncalibrated, or unverified, the decision is REVIEW.
  3. FAIL is never produced merely because an image looks unusual or deviates
     from nominal values without a configured tolerance. FAIL requires a
     clearly defined, reliable, and explicitly configured failure condition
     (such as an explicit tolerance violation on a calibrated measurement).
  4. PASS is only produced when all required measurements are available,
     calibration status is adequate (CALIBRATED), no configured failure
     condition is violated, and all intersection/geometry evidence is normal.
  5. Current representative mesh samples with provisional single-axis
     calibration and unconfigured tolerances must NEVER produce FAIL; they
     contribute to REVIEW.
  6. Material properties (tensile strength, weld shear strength, coating)
     are never claimed or evaluated by visual inspection.
"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from config.settings import (
    CALIBRATION_CAVEAT_PROVISIONAL,
    CALIBRATION_CAVEAT_UNVALIDATED_ESTIMATE,
    SAMPLE_VS_PROFILE_CAVEAT,
)
from core.mesh_spacing import (
    MeshSpacingResult,
    ProductSpacingProfile,
    SpacingComparisonResult,
    compare_against_profile,
)
from core.weld_intersection import WeldIntersectionResult
from core.wire_detection import WireGridDetectionResult

InspectionStatus = Literal["PASS", "FAIL", "REVIEW"]


class InspectionDecisionError(Exception):
    """Raised when inspection decision cannot be evaluated due to invalid inputs."""


@dataclass
class InspectionDecision:
    """Structured, factual record of an inspection decision.

    final_status: exactly one of "PASS", "FAIL", "REVIEW".
    reasons: list of transparent, factual statements explaining the decision.
    spacing_status: summary status of spacing measurements.
    intersection_status: summary status of intersection appearance.
    calibration_status: summary status of calibration across axes.
    configured_tolerance_status: status of tolerance configuration and compliance.
    supporting_evidence: dictionary of underlying numerical/factual metrics.
    source_name: identifier of the inspected sample/image.
    notes: additional engineering context.
    """
    source_name: str
    final_status: InspectionStatus
    reasons: List[str] = field(default_factory=list)
    spacing_status: str = "NOT_EVALUATED"
    intersection_status: str = "NOT_EVALUATED"
    calibration_status: str = "NOT_EVALUATED"
    configured_tolerance_status: str = "NOT_EVALUATED"
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""


def make_inspection_decision(
    wire_result: Optional[WireGridDetectionResult] = None,
    weld_result: Optional[WeldIntersectionResult] = None,
    spacing_result: Optional[MeshSpacingResult] = None,
    profile: Optional[ProductSpacingProfile] = None,
    source_name: Optional[str] = None,
) -> InspectionDecision:
    """Evaluate inspection evidence and produce a PASS / FAIL / REVIEW decision.

    Args:
        wire_result: WireGridDetectionResult from core.wire_detection.
        weld_result: WeldIntersectionResult from core.weld_intersection.
        spacing_result: MeshSpacingResult from core.mesh_spacing.
        profile: Optional ProductSpacingProfile with nominals/tolerances.
        source_name: Optional name for reporting (defaults to source_name in results).

    Returns:
        InspectionDecision with final_status in {"PASS", "FAIL", "REVIEW"}.

    Raises:
        InspectionDecisionError: if inputs are of completely invalid types or
            all inputs are None.
    """
    if wire_result is None and weld_result is None and spacing_result is None:
        raise InspectionDecisionError("make_inspection_decision received no inspection evidence.")

    # Validate types when inputs are provided
    if wire_result is not None and not isinstance(wire_result, WireGridDetectionResult):
        raise InspectionDecisionError(
            f"Invalid wire_result type: {type(wire_result).__name__}. Expected WireGridDetectionResult."
        )
    if weld_result is not None and not isinstance(weld_result, WeldIntersectionResult):
        raise InspectionDecisionError(
            f"Invalid weld_result type: {type(weld_result).__name__}. Expected WeldIntersectionResult."
        )
    if spacing_result is not None and not isinstance(spacing_result, MeshSpacingResult):
        raise InspectionDecisionError(
            f"Invalid spacing_result type: {type(spacing_result).__name__}. Expected MeshSpacingResult."
        )
    if profile is not None and not isinstance(profile, ProductSpacingProfile):
        raise InspectionDecisionError(
            f"Invalid profile type: {type(profile).__name__}. Expected ProductSpacingProfile."
        )

    # Determine reporting name
    name = source_name
    if not name:
        if spacing_result and spacing_result.source_name:
            name = spacing_result.source_name
        elif weld_result and weld_result.source_name:
            name = weld_result.source_name
        elif wire_result and wire_result.source_name:
            name = wire_result.source_name
        else:
            name = "unknown_source"

    fail_reasons: List[str] = []
    review_reasons: List[str] = []
    evidence: Dict[str, Any] = {}

    # -------------------------------------------------------------------------
    # 1. Evaluate Wire Detection Evidence
    # -------------------------------------------------------------------------
    if wire_result is None:
        review_reasons.append("Missing required wire detection evidence.")
        evidence["wire_detection"] = None
    else:
        evidence["wire_detection"] = {
            "num_horizontal_wires": wire_result.num_horizontal_wires,
            "num_vertical_wires": wire_result.num_vertical_wires,
            "num_intersections": wire_result.num_intersections,
            "expected_intersections": wire_result.expected_intersections,
            "intersection_completeness": round(wire_result.intersection_completeness, 4),
        }
        if wire_result.num_horizontal_wires < 2 or wire_result.num_vertical_wires < 2:
            review_reasons.append(
                f"Insufficient wire count: found {wire_result.num_horizontal_wires} horizontal and "
                f"{wire_result.num_vertical_wires} vertical wires (minimum 2 on each axis required for mesh aperture)."
            )
        elif wire_result.intersection_completeness < 1.0:
            review_reasons.append(
                f"Incomplete grid intersection coverage: {wire_result.num_intersections}/"
                f"{wire_result.expected_intersections} expected intersections detected "
                f"({wire_result.intersection_completeness * 100:.1f}% completeness)."
            )

    # -------------------------------------------------------------------------
    # 2. Evaluate Weld / Intersection Appearance Evidence
    # -------------------------------------------------------------------------
    if weld_result is None:
        review_reasons.append("Missing required weld/intersection analysis evidence.")
        intersection_status = "NOT_EVALUATED"
        evidence["weld_intersection"] = None
    else:
        evidence["weld_intersection"] = {
            "num_analyzed": weld_result.num_analyzed,
            "num_normal": weld_result.num_normal,
            "num_potentially_anomalous": weld_result.num_potentially_anomalous,
            "num_insufficient_evidence": weld_result.num_insufficient_evidence,
        }
        if weld_result.num_analyzed == 0:
            review_reasons.append("No intersections available for visual appearance analysis.")
            intersection_status = "NO_INTERSECTIONS"
        elif weld_result.num_potentially_anomalous > 0:
            review_reasons.append(
                f"{weld_result.num_potentially_anomalous} intersection(s) flagged POTENTIALLY_ANOMALOUS "
                f"(OBSERVATION - HUMAN VERIFICATION REQUIRED; visual arm mismatch)."
            )
            intersection_status = "ANOMALIES_DETECTED"
        elif weld_result.num_insufficient_evidence > 0:
            review_reasons.append(
                f"{weld_result.num_insufficient_evidence} intersection(s) have INSUFFICIENT_EVIDENCE "
                f"(boundary clipping or low contrast center)."
            )
            intersection_status = "INSUFFICIENT_EVIDENCE"
        else:
            intersection_status = "ALL_NORMAL"

    # -------------------------------------------------------------------------
    # 3. Evaluate Spacing & Calibration Evidence
    # -------------------------------------------------------------------------
    if spacing_result is None:
        review_reasons.append("Missing required mesh spacing measurement evidence.")
        spacing_status = "NOT_EVALUATED"
        calibration_status = "NOT_EVALUATED"
        configured_tolerance_status = "NOT_EVALUATED"
        evidence["mesh_spacing"] = None
    else:
        all_spacings = spacing_result.all_spacings
        evidence["mesh_spacing"] = {
            "num_vertical_spacings": spacing_result.num_vertical_spacings,
            "num_horizontal_spacings": spacing_result.num_horizontal_spacings,
            "mean_vertical_spacing_px": spacing_result.mean_vertical_spacing_px,
            "mean_vertical_spacing_mm": spacing_result.mean_vertical_spacing_mm,
            "mean_horizontal_spacing_px": spacing_result.mean_horizontal_spacing_px,
            "mean_horizontal_spacing_mm": spacing_result.mean_horizontal_spacing_mm,
        }

        if not all_spacings:
            review_reasons.append("No spacing intervals detected between adjacent wires.")
            spacing_status = "NO_SPACINGS_MEASURED"
            calibration_status = "NO_SPACINGS"
        else:
            # Check calibration status across all intervals
            statuses = {s.calibration_status for s in all_spacings}
            if statuses == {"CALIBRATED"}:
                calibration_status = "CALIBRATED"
            elif "UNVALIDATED ESTIMATE" in statuses and "UNCALIBRATED" in statuses:
                calibration_status = "UNVALIDATED_ESTIMATE_AND_UNCALIBRATED"
            elif "PROVISIONAL" in statuses and "UNCALIBRATED" in statuses:
                calibration_status = "PROVISIONAL_AND_UNCALIBRATED"
            elif "UNVALIDATED ESTIMATE" in statuses:
                calibration_status = "UNVALIDATED_ESTIMATE"
            elif "PROVISIONAL" in statuses:
                calibration_status = "PROVISIONAL"
            elif statuses == {"UNCALIBRATED"}:
                calibration_status = "UNCALIBRATED"
            else:
                calibration_status = "_".join(sorted(statuses))

            if "UNVALIDATED ESTIMATE" in statuses:
                review_reasons.append(CALIBRATION_CAVEAT_UNVALIDATED_ESTIMATE)
            if "PROVISIONAL" in statuses:
                review_reasons.append(CALIBRATION_CAVEAT_PROVISIONAL)
            if "UNCALIBRATED" in statuses:
                review_reasons.append(
                    "Horizontal spacing is UNCALIBRATED (preserving documented position-dependent "
                    "horizontal calibration limitation; no single global scale invented)."
                )

        # ---------------------------------------------------------------------
        # 4. Evaluate Profile & Tolerances (if provided)
        # ---------------------------------------------------------------------
        if profile is None:
            configured_tolerance_status = "NO_PROFILE_SPECIFIED"
            spacing_status = "MEASURED_WITHOUT_PROFILE"
        else:
            evidence["product_profile"] = {
                "profile_id": profile.profile_id,
                "name": profile.name,
                "nominal_vertical_spacing_mm": profile.nominal_vertical_spacing_mm,
                "nominal_horizontal_spacing_mm": profile.nominal_horizontal_spacing_mm,
                "vertical_tolerance_mm": profile.vertical_tolerance_mm,
                "horizontal_tolerance_mm": profile.horizontal_tolerance_mm,
                "sample_vs_profile_caveat": SAMPLE_VS_PROFILE_CAVEAT,
            }

            has_tolerance = (
                profile.vertical_tolerance_mm is not None
                or profile.horizontal_tolerance_mm is not None
            )

            if not has_tolerance:
                configured_tolerance_status = "NO_TOLERANCE_CONFIGURED"
                spacing_status = "PROFILE_WITHOUT_TOLERANCE"
                review_reasons.append(
                    f"Product profile {profile.profile_id} ({profile.name}) has no validated tolerance "
                    f"configured. Measured deviation from nominal cannot produce an acceptance decision."
                )
            else:
                # Tolerance is configured -> evaluate compliance
                comp_result: SpacingComparisonResult = compare_against_profile(spacing_result, profile)
                evidence["profile_comparison"] = [
                    {
                        "axis": c.axis,
                        "index": c.index,
                        "measured_spacing_mm": c.measured_spacing_mm,
                        "nominal_spacing_mm": c.nominal_spacing_mm,
                        "deviation_mm": c.deviation_mm,
                        "tolerance_mm": c.tolerance_mm,
                        "status": c.status,
                    }
                    for c in comp_result.comparisons
                ]

                has_violation = False
                has_unvalidated_tolerance_check = False
                for c in comp_result.comparisons:
                    if c.status == "OUT_OF_TOLERANCE":
                        has_violation = True
                        fail_reasons.append(
                            f"Spacing interval {c.axis}[{c.index}] ({c.measured_spacing_mm} mm) "
                            f"violates configured tolerance {c.nominal_spacing_mm} ± {c.tolerance_mm} mm "
                            f"(deviation: {c.deviation_mm:+.2f} mm)."
                        )
                    elif c.status in ("UNCALIBRATED", "UNVALIDATED_CALIBRATION") and (
                        (c.axis == "vertical" and profile.vertical_tolerance_mm is not None)
                        or (c.axis == "horizontal" and profile.horizontal_tolerance_mm is not None)
                    ):
                        has_unvalidated_tolerance_check = True
                        if c.status == "UNCALIBRATED":
                            detail = "measurement is uncalibrated"
                        else:
                            detail = (
                                "calibration basis is an unvalidated estimate, not a "
                                "validated calibration"
                            )
                        review_reasons.append(
                            f"Cannot evaluate configured tolerance on {c.axis}[{c.index}]: "
                            f"{detail}."
                        )

                if has_violation:
                    configured_tolerance_status = "TOLERANCE_VIOLATED"
                    spacing_status = "OUT_OF_TOLERANCE"
                elif has_unvalidated_tolerance_check:
                    # A tolerance is configured, but at least one axis's calibration
                    # basis has not passed validation. Do NOT claim WITHIN_TOLERANCE
                    # from an unvalidated/uncalibrated measurement.
                    configured_tolerance_status = "CANNOT_EVALUATE_UNVALIDATED_CALIBRATION"
                    spacing_status = "CANNOT_EVALUATE"
                else:
                    configured_tolerance_status = "WITHIN_TOLERANCE"
                    spacing_status = "WITHIN_TOLERANCE"

    # -------------------------------------------------------------------------
    # 5. Determine Final Status (FAIL > REVIEW > PASS)
    # -------------------------------------------------------------------------
    if fail_reasons:
        final_status: InspectionStatus = "FAIL"
        reasons = fail_reasons
        notes = (
            "INSPECTION FAIL: One or more explicit, validated failure conditions / tolerances "
            "were violated on calibrated measurements."
        )
    elif review_reasons:
        final_status: InspectionStatus = "REVIEW"
        reasons = review_reasons
        notes = (
            "INSPECTION REVIEW: Available evidence is provisional, uncalibrated, anomalous, "
            "or incomplete. Manual verification is required before making an acceptance decision."
        )
    else:
        final_status: InspectionStatus = "PASS"
        reasons = [
            "All required inspection evidence is present.",
            "All spacing measurements are fully calibrated and compliant.",
            "All wire intersection visual appearance regions are normal.",
            "No configured failure conditions or anomalies detected.",
        ]
        notes = "INSPECTION PASS: Fully calibrated measurements and normal geometry meet all criteria."

    return InspectionDecision(
        source_name=name,
        final_status=final_status,
        reasons=reasons,
        spacing_status=spacing_status,
        intersection_status=intersection_status,
        calibration_status=calibration_status,
        configured_tolerance_status=configured_tolerance_status,
        supporting_evidence=evidence,
        notes=notes,
    )


def save_inspection_decision(
    decision: InspectionDecision,
    output_dir: Union[str, Path],
) -> Path:
    """Save an InspectionDecision as JSON following existing project patterns.
    Never written into 02_DATASET.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(decision.source_name).stem
    output_path = output_dir / f"inspection_decision_{stem}.json"

    with open(output_path, "w") as f:
        json.dump(asdict(decision), f, indent=2)

    return output_path
