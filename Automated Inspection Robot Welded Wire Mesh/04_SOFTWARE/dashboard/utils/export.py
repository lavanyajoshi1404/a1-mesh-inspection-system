"""
Report generation and export utilities for the A1 Mesh Inspection Dashboard.

Exports factual, reproducible inspection records:
- Structured JSON Record
- Clean Text / Printable Report
- CSV Wire Spacing Table
- Saves inspection artifacts to 04_SOFTWARE/data/results/
"""

import csv
import io
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import cv2

from core.inspection_decision import save_inspection_decision
from core.mesh_spacing import save_mesh_spacing_result
from core.weld_intersection import save_weld_intersection_result
from core.wire_detection import save_wire_detection_result


def generate_json_report(result) -> str:
    """Serialize the full inspection result into a standardized JSON report."""
    payload = {
        "inspection_id": result.inspection_id,
        "timestamp": result.timestamp,
        "source_name": result.source_name,
        "input_source_type": result.input_source_type,
        "final_classification": result.final_classification,
        "decision": {
            "final_status": result.decision.final_status,
            "reasons": result.decision.reasons,
            "spacing_status": result.decision.spacing_status,
            "intersection_status": result.decision.intersection_status,
            "calibration_status": result.decision.calibration_status,
            "configured_tolerance_status": result.decision.configured_tolerance_status,
            "notes": result.decision.notes,
        },
        "grid_statistics": {
            "image_width_px": result.wire_result.image_width,
            "image_height_px": result.wire_result.image_height,
            "horizontal_wires_count": result.wire_result.num_horizontal_wires,
            "vertical_wires_count": result.wire_result.num_vertical_wires,
            "detected_intersections": result.wire_result.num_intersections,
            "expected_intersections": result.wire_result.expected_intersections,
            "intersection_completeness": round(result.wire_result.intersection_completeness, 4),
        },
        "weld_statistics": {
            "total_analyzed": result.weld_result.num_analyzed,
            "normal_count": result.weld_result.num_normal,
            "potentially_anomalous_count": result.weld_result.num_potentially_anomalous,
            "insufficient_evidence_count": result.weld_result.num_insufficient_evidence,
        },
        "spacing_statistics": {
            "num_vertical_spacings": result.spacing_result.num_vertical_spacings,
            "num_horizontal_spacings": result.spacing_result.num_horizontal_spacings,
            "mean_vertical_spacing_px": result.spacing_result.mean_vertical_spacing_px,
            "mean_vertical_spacing_mm": result.spacing_result.mean_vertical_spacing_mm,
            "mean_horizontal_spacing_px": result.spacing_result.mean_horizontal_spacing_px,
            "mean_horizontal_spacing_mm": result.spacing_result.mean_horizontal_spacing_mm,
            "vertical_spacings": [asdict(s) for s in result.spacing_result.vertical_spacings],
            "horizontal_spacings": [asdict(s) for s in result.spacing_result.horizontal_spacings],
        },
        "anomalies": [
            {
                "id": a.id,
                "category": a.category,
                "location": a.location,
                "evidence": a.evidence,
                "status": a.status,
                "coordinates_px": a.coordinates_px,
            }
            for a in result.anomalies
        ],
    }
    return json.dumps(payload, indent=2)


def generate_text_report(result) -> str:
    """Generate a clean, printable plain text engineering inspection report."""
    lines = []
    lines.append("=" * 72)
    lines.append("A-1 MESH INSPECTION SYSTEM — QUALITY INSPECTION REPORT")
    lines.append("Automated Vision-Based Quality Inspection for Welded Wire Mesh")
    lines.append("=" * 72)
    lines.append(f"Inspection ID:         {result.inspection_id}")
    lines.append(f"Timestamp:             {result.timestamp}")
    lines.append(f"Input Source Type:     {result.input_source_type}")
    lines.append(f"Image Name:            {result.source_name}")
    lines.append(f"Image Resolution:      {result.image_info.width} x {result.image_info.height} px")
    lines.append("-" * 72)
    lines.append(f"FINAL CLASSIFICATION:  {result.final_classification} (Status: {result.decision.final_status})")
    lines.append("-" * 72)
    lines.append("DECISION REASONS & LIMITATIONS:")
    for idx, reason in enumerate(result.decision.reasons, 1):
        lines.append(f"  {idx}. {reason}")
    lines.append("-" * 72)
    lines.append("GRID GEOMETRY METRICS:")
    lines.append(f"  Horizontal Wires:     {result.wire_result.num_horizontal_wires}")
    lines.append(f"  Vertical Wires:       {result.wire_result.num_vertical_wires}")
    lines.append(
        f"  Intersections:        {result.wire_result.num_intersections} / "
        f"{result.wire_result.expected_intersections} expected "
        f"({result.wire_result.intersection_completeness * 100:.1f}% completeness)"
    )
    lines.append("-" * 72)
    lines.append("WELD / INTERSECTION REGION ANALYSIS:")
    lines.append(f"  Total Analyzed:       {result.weld_result.num_analyzed}")
    lines.append(f"  Normal:               {result.weld_result.num_normal}")
    lines.append(f"  Potentially Anomalous:{result.weld_result.num_potentially_anomalous} (Human Verification Required)")
    lines.append(f"  Insufficient Evidence:{result.weld_result.num_insufficient_evidence}")
    lines.append("-" * 72)
    lines.append("MESH SPACING MEASUREMENTS:")
    lines.append(
        f"  Vertical Spacings:    {result.spacing_result.num_vertical_spacings} intervals | "
        f"Mean: {result.spacing_result.mean_vertical_spacing_px or 0:.1f} px = "
        f"{result.spacing_result.mean_vertical_spacing_mm or 'N/A'} mm "
        f"({result.spacing_result.vertical_spacings[0].calibration_status if result.spacing_result.vertical_spacings else 'N/A'})"
    )
    lines.append(
        f"  Horizontal Spacings:  {result.spacing_result.num_horizontal_spacings} intervals | "
        f"Mean: {result.spacing_result.mean_horizontal_spacing_px or 0:.1f} px = "
        f"{result.spacing_result.mean_horizontal_spacing_mm or 'N/A'} mm "
        f"({result.spacing_result.horizontal_spacings[0].calibration_status if result.spacing_result.horizontal_spacings else 'N/A'})"
    )
    lines.append("-" * 72)
    lines.append(f"ANOMALY SUMMARY ({len(result.anomalies)} items):")
    for a in result.anomalies:
        coord = f" at {a.coordinates_px}" if a.coordinates_px else ""
        lines.append(f"  [{a.id}] {a.category} — {a.location}{coord}: {a.status}")
        lines.append(f"      Evidence: {a.evidence}")
    lines.append("=" * 72)
    lines.append("ENGINEERING NOTICE: Visual inspection evaluates optical geometry only.")
    lines.append("Tensile strength, weld shear strength, and coating adhesion require physical destructive testing.")
    lines.append("=" * 72)
    return "\n".join(lines)


def generate_csv_spacings(result) -> str:
    """Generate CSV string of all individual spacing measurements."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Axis", "Index", "Wire_1_Index", "Wire_2_Index",
        "Wire_1_Px", "Wire_2_Px", "Pixel_Spacing_Px",
        "Measured_Spacing_Mm", "Calibration_Used_Px_Per_Mm",
        "Calibration_Status", "Midpoint_Px", "Notes",
    ])
    for s in result.spacing_result.all_spacings:
        writer.writerow([
            s.axis, s.index, s.wire_index_1, s.wire_index_2,
            s.wire_position_1_px, s.wire_position_2_px, s.pixel_spacing,
            s.measured_spacing, s.calibration_used,
            s.calibration_status, s.location_px, s.notes,
        ])
    return output.getvalue()


def save_inspection_to_disk(result, output_dir: Union[str, Path]) -> Dict[str, Path]:
    """Save all inspection artifacts to disk in a reproducible manner."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source_name).stem

    saved = {}

    # 1. Decision JSON
    saved["decision_json"] = save_inspection_decision(result.decision, out_dir)

    # 2. Wire detection JSON
    saved["wire_json"] = save_wire_detection_result(result.wire_result, out_dir)

    # 3. Weld intersection JSON
    saved["weld_json"] = save_weld_intersection_result(result.weld_result, out_dir)

    # 4. Spacing JSON
    saved["spacing_json"] = save_mesh_spacing_result(result.spacing_result, out_dir)

    # 5. Overlays
    if result.grid_overlay is not None:
        p = out_dir / f"wire_detection_{stem}_overlay.jpg"
        cv2.imwrite(str(p), result.grid_overlay)
        saved["grid_overlay"] = p

    if result.intersection_overlay is not None:
        p = out_dir / f"weld_intersection_{stem}_overlay.jpg"
        cv2.imwrite(str(p), result.intersection_overlay)
        saved["intersection_overlay"] = p

    if result.heatmap_overlay is not None:
        p = out_dir / f"heatmap_{stem}_overlay.jpg"
        cv2.imwrite(str(p), result.heatmap_overlay)
        saved["heatmap_overlay"] = p

    if result.spacing_overlay is not None:
        p = out_dir / f"mesh_spacing_{stem}_overlay.jpg"
        cv2.imwrite(str(p), result.spacing_overlay)
        saved["spacing_overlay"] = p

    # 6. Text Report
    text_path = out_dir / f"inspection_report_{stem}.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(generate_text_report(result))
    saved["text_report"] = text_path

    return saved
