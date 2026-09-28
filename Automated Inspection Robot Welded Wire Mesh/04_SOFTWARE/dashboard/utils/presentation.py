"""Dashboard-only view model helpers.

Formats existing PipelineInspectionResult evidence without changing
the inspection engine, decision rules, or result objects.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def _value(value: Any, unit: str = "", digits: int = 2, empty: str = "Not available") -> str:
    if value is None:
        return empty
    if isinstance(value, float):
        value = f"{value:.{digits}f}"
    return f"{value}{unit}"


def _profile(result) -> Dict[str, Any]:
    return result.decision.supporting_evidence.get("product_profile", {}) or {}


def _axis_status(measurements: Sequence[Any], empty: str = "Not evaluated") -> str:
    statuses = sorted({m.calibration_status for m in measurements})
    return ", ".join(statuses) if statuses else empty


def _display_tolerance(status: str) -> str:
    mapping = {
        "NO_TOLERANCE_CONFIGURED": "NOT CONFIGURED",
        "NOT_EVALUATED": "NOT EVALUATED",
        "WITHIN_TOLERANCE": "WITHIN TOLERANCE",
        "OUT_OF_TOLERANCE": "OUT OF TOLERANCE",
        "CANNOT_EVALUATE_UNVALIDATED_CALIBRATION": "CANNOT EVALUATE (UNVALIDATED CALIBRATION)",
    }
    return mapping.get(status, status.replace("_", " "))


def calibration_rows(result) -> List[Dict[str, str]]:
    rows = []
    for axis, measurements in (
        ("Vertical / Y", result.spacing_result.vertical_spacings),
        ("Horizontal / X", result.spacing_result.horizontal_spacings),
    ):
        scales = sorted({m.calibration_used for m in measurements if m.calibration_used is not None})
        statuses = sorted({m.calibration_status for m in measurements})
        rows.append(
            {
                "Axis": axis,
                "Scale": ", ".join(f"{scale:.2f} px/mm" for scale in scales) or "Not available",
                "Status": ", ".join(statuses) or "Not evaluated",
            }
        )
    return rows


def spacing_rows(result) -> List[Dict[str, str]]:
    return [
        {
            "Axis": m.axis.upper(),
            "Interval": f"{m.wire_index_1} → {m.wire_index_2}",
            "Pixel pitch": _value(m.pixel_spacing, " px", 1),
            "Measured pitch": _value(m.measured_spacing, " mm", 2),
            "Calibration": m.calibration_status,
        }
        for m in result.spacing_result.all_spacings
    ]


# M-2: categories that represent a real, per-location visual/optical finding
# on the sample itself, as opposed to a procedural/methodology note about the
# inspection's own evidence quality (missing intersections, calibration
# caveats). Used to make the 8-vs-12 distinction between the summary metric
# ("8 potential visual anomalies") and the full findings table (12 rows)
# explicit, rather than implicit - see finding_rows() and finding_counts().
VISUAL_FINDING_CATEGORIES = {"Intersection Visual Arm Mismatch"}


def finding_rows(result) -> List[Dict[str, str]]:
    return [
        {
            "#": str(i.id),
            "Type": "Visual Finding" if i.category in VISUAL_FINDING_CATEGORIES else "Methodology / Calibration Note",
            "Finding": i.category,
            "Location": i.location,
            "Status": i.status,
            "Evidence": i.evidence,
        }
        for i in result.anomalies
    ]


def finding_counts(result) -> Dict[str, int]:
    """Breakdown backing the 'why does the summary say 8 but the table shows
    12' distinction: real visual findings vs procedural/methodology notes."""
    visual = sum(1 for i in result.anomalies if i.category in VISUAL_FINDING_CATEGORIES)
    total = len(result.anomalies)
    return {"visual": visual, "methodology": total - visual, "total": total}


def evidence_statements(result) -> List[str]:
    """Operator-facing evidence lines derived only from pipeline objects."""
    wire = result.wire_result
    weld = result.weld_result
    spacing = result.spacing_result
    decision = result.decision
    statements: List[str] = []

    statements.append(
        f"{wire.num_intersections}/{wire.expected_intersections} intersections detected"
    )
    if weld.num_potentially_anomalous:
        statements.append(
            f"{weld.num_potentially_anomalous} potential visual anomalies require verification"
        )
    if weld.num_insufficient_evidence:
        statements.append(
            f"{weld.num_insufficient_evidence} intersection region(s) have insufficient visual evidence"
        )

    vertical_status = _axis_status(spacing.vertical_spacings)
    horizontal_status = _axis_status(spacing.horizontal_spacings)
    if "UNVALIDATED ESTIMATE" in vertical_status:
        statements.append("vertical scale basis: UNVALIDATED ESTIMATE")
    elif "PROVISIONAL" in vertical_status:
        statements.append("vertical calibration provisional")
    if "UNCALIBRATED" in horizontal_status:
        statements.append("horizontal calibration unavailable")
    if decision.configured_tolerance_status == "NO_TOLERANCE_CONFIGURED":
        statements.append("no configured product tolerance")
    return statements


def limitation_rows(result) -> List[Dict[str, str]]:
    decision = result.decision
    spacing = result.spacing_result
    rows: List[Dict[str, str]] = []
    vertical_status = _axis_status(spacing.vertical_spacings)
    horizontal_status = _axis_status(spacing.horizontal_spacings)
    if "UNVALIDATED ESTIMATE" in vertical_status:
        rows.append(
            {
                "Limitation": "Unvalidated scale estimate",
                "Scope": "Vertical axis",
                "Implication": "Millimetre spacing uses a fixed, unvalidated single-axis scale estimate (11.0 px/mm), not a statistically validated or certified calibration.",
            }
        )
    elif "PROVISIONAL" in vertical_status:
        rows.append(
            {
                "Limitation": "Provisional calibration",
                "Scope": "Vertical axis",
                "Implication": "Millimetre spacing is a single-axis provisional scale, not a certified 2D calibration.",
            }
        )
    if "UNCALIBRATED" in horizontal_status:
        rows.append(
            {
                "Limitation": "Uncalibrated measurements",
                "Scope": "Horizontal axis",
                "Implication": "Horizontal pitch is reported in pixels only.",
            }
        )
    if decision.configured_tolerance_status == "NO_TOLERANCE_CONFIGURED":
        rows.append(
            {
                "Limitation": "No tolerance configured",
                "Scope": "Product profile",
                "Implication": "Spacing cannot be judged PASS/FAIL against a validated product tolerance.",
            }
        )
    rows.append(
        {
            "Limitation": "Visual evidence limitations",
            "Scope": "Intersection appearance",
            "Implication": "Potentially anomalous crossings are optical/geometric flags for review, not confirmed weld defects.",
        }
    )
    return rows


def visual_mode_evidence(result, mode: str) -> Dict[str, Any]:
    """Evidence panel content for the selected visualization only."""
    vm = inspection_view_model(result)
    mode = (mode or "ORIGINAL").upper()
    rows: List[tuple[str, str]]
    notes: List[str]
    if mode == "GRID":
        rows = [
            ("Horizontal wires", str(vm["num_horizontal"])),
            ("Vertical wires", str(vm["num_vertical"])),
            ("Detected intersections", str(vm["num_intersections"])),
            ("Expected intersections", str(vm["expected_intersections"])),
            ("Completeness", vm["completeness"]),
        ]
        notes = [
            "Overlay shows detected horizontal wires, vertical wires, and crossings from the existing grid detector."
        ]
    elif mode == "INTERSECTIONS":
        rows = [
            ("Analyzed", str(vm["num_analyzed"])),
            ("Normal", str(vm["num_normal"])),
            ("Potentially anomalous", str(vm["potential_anomalies"])),
            ("Insufficient evidence", str(vm["insufficient_evidence"])),
        ]
        notes = [
            "POTENTIALLY_ANOMALOUS is visual-arm mismatch evidence requiring review. It is not a confirmed weld defect."
        ]
    elif mode == "HEATMAP":
        rows = [
            ("Visual findings", str(vm["potential_anomalies"])),
            ("Insufficient evidence", str(vm["insufficient_evidence"])),
            ("Incomplete crossings", str(max(vm["expected_intersections"] - vm["num_intersections"], 0))),
            ("Rust-like area", f"{getattr(result, 'rust_area_percentage', 0.0):.2f}%"),
            ("Rust-like regions", str(getattr(result, "rust_regions_count", 0))),
        ]
        notes = [
            "Highlighted regions aggregate measured intersection-arm mismatches, incomplete crossings, and calibration limitations.",
            "Amber areas mark rust-like surface discoloration estimated from image color; verify coating condition visually.",
            "This is visual/geometric evidence only. It is not AI confidence, ML probability, or prediction confidence.",
        ]
    elif mode == "SPACING":
        rows = [
            ("Vertical spacing", vm["vertical_spacing_display"]),
            ("Vertical calibration", vm["vertical_calibration"]),
            ("Horizontal spacing", vm["horizontal_spacing_display"]),
            ("Horizontal calibration", vm["horizontal_calibration"]),
            ("Tolerance", vm["tolerance_display"]),
        ]
        notes = [
            "Spacing values are taken from MeshSpacingResult. Uncalibrated axes remain pixel-only."
        ]
    else:
        rows = [
            ("Source", vm["source"]),
            ("Acquisition", vm["source_type"]),
            ("Source size", vm["image"]),
            ("Processed size", vm["processing"]),
        ]
        notes = ["Unmodified acquisition frame used as the inspection source."]
    return {"mode": mode, "rows": rows, "notes": notes}


def inspection_view_model(result) -> Dict[str, Any]:
    """Return one consistent, presentation-safe representation of a run."""
    wire = result.wire_result
    weld = result.weld_result
    spacing = result.spacing_result
    decision = result.decision
    profile = _profile(result)
    vertical_cal = _axis_status(spacing.vertical_spacings)
    horizontal_cal = _axis_status(spacing.horizontal_spacings)

    if spacing.mean_vertical_spacing_mm is not None:
        vertical_spacing_display = _value(spacing.mean_vertical_spacing_mm, " mm", 2)
    else:
        vertical_spacing_display = _value(spacing.mean_vertical_spacing_px, " px", 1)

    if spacing.mean_horizontal_spacing_mm is not None:
        horizontal_spacing_display = _value(spacing.mean_horizontal_spacing_mm, " mm", 2)
    elif "UNCALIBRATED" in horizontal_cal:
        horizontal_spacing_display = "UNCALIBRATED"
    else:
        horizontal_spacing_display = _value(spacing.mean_horizontal_spacing_px, " px", 1)

    otsu: Optional[float] = getattr(result.preprocessing_result, "otsu_threshold", None)

    return {
        "id": result.inspection_id,
        "timestamp": result.timestamp,
        "source": result.source_name,
        "source_type": result.input_source_type,
        "classification": result.final_classification,
        "decision": decision.final_status,
        "decision_reasons": list(decision.reasons),
        "decision_note": decision.notes,
        "image": f"{result.image_info.width} × {result.image_info.height} px, {result.image_info.channels} channel(s)",
        "image_width": result.image_info.width,
        "image_height": result.image_info.height,
        "channels": result.image_info.channels,
        "processing": (
            f"{result.preprocessing_result.processed_width} × "
            f"{result.preprocessing_result.processed_height} px "
            f"(scale {result.preprocessing_result.resize_scale:.3f})"
        ),
        "processed_width": result.preprocessing_result.processed_width,
        "processed_height": result.preprocessing_result.processed_height,
        "resize_scale": result.preprocessing_result.resize_scale,
        "otsu": _value(otsu, "", 1),
        "num_horizontal": wire.num_horizontal_wires,
        "num_vertical": wire.num_vertical_wires,
        "grid": f"{wire.num_horizontal_wires} H × {wire.num_vertical_wires} V",
        "angle_h": _value(wire.mean_horizontal_angle_deviation_deg, "°", 2),
        "angle_v": _value(wire.mean_vertical_angle_deviation_deg, "°", 2),
        "num_intersections": wire.num_intersections,
        "expected_intersections": wire.expected_intersections,
        "completeness": f"{wire.intersection_completeness * 100:.0f}%",
        "intersections": f"{wire.num_intersections} / {wire.expected_intersections}",
        "num_analyzed": weld.num_analyzed,
        "num_normal": weld.num_normal,
        "potential_anomalies": weld.num_potentially_anomalous,
        "insufficient_evidence": weld.num_insufficient_evidence,
        "vertical_spacing": _value(spacing.mean_vertical_spacing_mm, " mm", 2),
        "vertical_spacing_px": _value(spacing.mean_vertical_spacing_px, " px", 1),
        "horizontal_spacing": _value(spacing.mean_horizontal_spacing_mm, " mm", 2),
        "horizontal_spacing_px": _value(spacing.mean_horizontal_spacing_px, " px", 1),
        "vertical_spacing_display": vertical_spacing_display,
        "horizontal_spacing_display": horizontal_spacing_display,
        "vertical_calibration": vertical_cal,
        "horizontal_calibration": horizontal_cal,
        "calibration": decision.calibration_status,
        "tolerance": decision.configured_tolerance_status,
        "tolerance_display": _display_tolerance(decision.configured_tolerance_status),
        "profile_id": profile.get("profile_id", "No profile"),
        "profile_name": profile.get("name", "Not specified"),
        "profile": f"{profile.get('profile_id', 'No profile')} — {profile.get('name', 'Not specified')}",
        "findings": finding_rows(result),
        "finding_counts": finding_counts(result),
        "spacing_rows": spacing_rows(result),
        "calibration_rows": calibration_rows(result),
        "evidence_statements": evidence_statements(result),
        "limitations": limitation_rows(result),
        "spacing_status": decision.spacing_status,
        "intersection_status": decision.intersection_status,
        "rust_area_percentage": getattr(result, "rust_area_percentage", 0.0),
        "rust_regions_count": getattr(result, "rust_regions_count", 0),
    }
