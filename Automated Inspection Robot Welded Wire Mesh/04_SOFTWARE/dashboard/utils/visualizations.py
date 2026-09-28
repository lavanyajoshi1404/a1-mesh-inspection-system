"""
Visualization generators for the A1 Mesh Inspection Dashboard.

Creates factual, evidence-based visual inspection overlays:
1. Grid Detection Overlay (actual detected horizontal/vertical wire extents and crossings)
2. Intersection / Weld Appearance Overlay (Normal green, Anomalous amber/red, Insufficient grey/yellow)
3. Spatially Aligned Anomaly Heatmap (evidence-based Gaussian hotspot blend with legend)
4. Wire Spacing Overlay (pixel spacing and mm conversion arrows)

Strict rules:
- No artificial random anomaly locations.
- No rainbow heatmaps; use Green (Normal), Yellow (Review), Red (Anomaly).
- Semi-transparent overlays so underlying physical wire mesh remains clearly visible.
"""

from typing import Optional, Tuple

import cv2
import numpy as np

from core.mesh_spacing import MeshSpacingResult, draw_mesh_spacing_overlay
from core.weld_intersection import WeldIntersectionResult
from core.wire_detection import WireGridDetectionResult


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    """Ensure the image array is a 3-channel BGR image."""
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image.copy()


def draw_grid_overlay(
    image: np.ndarray,
    wire_result: WireGridDetectionResult,
) -> np.ndarray:
    """Render detected horizontal and vertical wires and their crossings.

    Uses the actual detected coordinate extents from core.wire_detection - does NOT
    draw a fake idealized grid.
    """
    overlay = _ensure_bgr(image)
    h, w = overlay.shape[:2]

    # Draw horizontal wires (cyan lines)
    for idx, hw in enumerate(wire_result.horizontal_wires):
        y = int(round(hw.position_px))
        x_min, x_max = int(round(hw.extent_px[0])), int(round(hw.extent_px[1]))
        cv2.line(overlay, (x_min, y), (x_max, y), (255, 200, 0), 2)  # Cyan/light blue
        cv2.putText(
            overlay, f"H{idx}: y={y}px", (min(x_max + 6, w - 110), max(y - 4, 15)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 220, 50), 1, cv2.LINE_AA
        )

    # Draw vertical wires (magenta lines)
    for idx, vw in enumerate(wire_result.vertical_wires):
        x = int(round(vw.position_px))
        y_min, y_max = int(round(vw.extent_px[0])), int(round(vw.extent_px[1]))
        cv2.line(overlay, (x, y_min), (x, y_max), (200, 50, 255), 2)  # Magenta/violet
        cv2.putText(
            overlay, f"V{idx}: x={x}px", (max(x - 25, 5), min(y_max + 16, h - 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (220, 80, 255), 1, cv2.LINE_AA
        )

    # Draw confirmed crossing points
    for isec in wire_result.intersections:
        cx, cy = int(round(isec.x_px)), int(round(isec.y_px))
        cv2.circle(overlay, (cx, cy), 6, (0, 255, 255), -1)  # Yellow crossing dot
        cv2.circle(overlay, (cx, cy), 8, (0, 100, 200), 1)

    # Summary statistics banner
    completeness_pct = wire_result.intersection_completeness * 100
    banner = (
        f"GRID DETECTION: {wire_result.num_horizontal_wires} H-Wires x {wire_result.num_vertical_wires} V-Wires | "
        f"Intersections: {wire_result.num_intersections}/{wire_result.expected_intersections} ({completeness_pct:.1f}% completeness)"
    )
    cv2.rectangle(overlay, (0, 0), (w, 28), (20, 25, 35), -1)
    cv2.putText(overlay, banner, (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)

    return overlay


def draw_intersection_overlay(
    image: np.ndarray,
    wire_result: WireGridDetectionResult,
    weld_result: WeldIntersectionResult,
) -> np.ndarray:
    """Render weld intersection appearance classifications.

    Color coding:
      - NORMAL -> Green marker
      - POTENTIALLY_ANOMALOUS -> Amber/Red marker with warning symbol
      - INSUFFICIENT_EVIDENCE -> Grey/Yellow marker
    """
    overlay = _ensure_bgr(image)
    h, w = overlay.shape[:2]

    # Map assessments by grid index
    assessment_map = {
        (a.horizontal_wire_index, a.vertical_wire_index): a
        for a in weld_result.assessments
    }

    radius = 18

    for isec in wire_result.intersections:
        cx, cy = int(round(isec.x_px)), int(round(isec.y_px))
        key = (isec.horizontal_wire_index, isec.vertical_wire_index)
        assessment = assessment_map.get(key)

        if assessment is None or assessment.status == "NORMAL":
            # Normal: Green ring and center dot
            color = (30, 200, 40)
            cv2.circle(overlay, (cx, cy), radius, color, 2)
            cv2.circle(overlay, (cx, cy), 4, color, -1)
        elif assessment.status == "POTENTIALLY_ANOMALOUS":
            # Potentially anomalous: Bright Amber/Orange square with exclamation
            color = (0, 140, 255)  # Amber in BGR
            cv2.rectangle(overlay, (cx - radius, cy - radius), (cx + radius, cy + radius), color, 2)
            cv2.circle(overlay, (cx, cy), 4, color, -1)
            cv2.putText(
                overlay, "!", (cx - 4, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA
            )
            # Label
            cv2.putText(
                overlay, f"ANOMALY H{isec.horizontal_wire_index}V{isec.vertical_wire_index}",
                (cx + radius + 4, cy + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA
            )
        else:
            # Insufficient evidence: Grey/Yellow dashed circle
            color = (160, 160, 160)
            cv2.circle(overlay, (cx, cy), radius, color, 2)
            cv2.putText(
                overlay, "?", (cx - 4, cy + 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA
            )

    # Top summary banner
    banner = (
        f"WELD / INTERSECTION REGIONS: {weld_result.num_normal} Normal (Green) | "
        f"{weld_result.num_potentially_anomalous} Potential Anomalies (Amber) | "
        f"{weld_result.num_insufficient_evidence} Insufficient Evidence (Grey)"
    )
    cv2.rectangle(overlay, (0, 0), (w, 28), (20, 25, 35), -1)
    cv2.putText(overlay, banner, (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)

    return overlay


def draw_anomaly_heatmap(
    image: np.ndarray,
    wire_result: WireGridDetectionResult,
    weld_result: WeldIntersectionResult,
    spacing_result: Optional[MeshSpacingResult] = None,
    alpha: float = 0.45,
    rust_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Generate a mesh-anomaly heatmap with optional rust-like oxidation overlay.

    Color meaning:
      - GREEN: Normal / confirmed regular wire intersection.
      - YELLOW: Review / uncertain evidence (boundary clipping, provisional scale, uncalibrated axis).
    - RED: Strong mesh anomaly (missing wire arm, arm mismatch, out-of-tolerance spacing).
    - AMBER: Rust-like surface discoloration flagged for operator review.

    Blended semi-transparently over the mesh image so underlying physical features remain visible.
    """
    base = _ensure_bgr(image)
    h, w = base.shape[:2]

    # Create a 3-channel color layer initialized to transparent black
    color_mask = np.zeros((h, w, 3), dtype=np.float32)
    weight_mask = np.zeros((h, w), dtype=np.float32)

    # Gaussian kernel radius based on wire spacing
    sigma = 38.0

    # 1. Render intersection-level evidence
    for a in weld_result.assessments:
        cx, cy = int(round(a.x_px)), int(round(a.y_px))

        # Assign BGR color based on evidence
        if a.status == "NORMAL":
            color = np.array([40, 210, 40], dtype=np.float32)   # Green
            intensity = 0.7
        elif a.status == "POTENTIALLY_ANOMALOUS":
            color = np.array([30, 30, 240], dtype=np.float32)   # Red
            intensity = 1.0
        else:
            color = np.array([30, 210, 240], dtype=np.float32)  # Yellow
            intensity = 0.85

        # Compute bounding patch for localized Gaussian splat
        patch_r = int(sigma * 2.5)
        x0, x1 = max(0, cx - patch_r), min(w, cx + patch_r + 1)
        y0, y1 = max(0, cy - patch_r), min(h, cy + patch_r + 1)

        xs = np.arange(x0, x1) - cx
        ys = np.arange(y0, y1) - cy
        xx, yy = np.meshgrid(xs, ys)
        dist_sq = xx ** 2 + yy ** 2
        kernel = np.exp(-dist_sq / (2 * sigma ** 2)) * intensity

        # Add to accumulator
        for c in range(3):
            color_mask[y0:y1, x0:x1, c] += kernel * color[c]
        weight_mask[y0:y1, x0:x1] += kernel

    # 2. Render missing intersection expected positions as Yellow (Review)
    expected_pairs = {
        (hi, vi)
        for hi in range(wire_result.num_horizontal_wires)
        for vi in range(wire_result.num_vertical_wires)
    }
    detected_pairs = {
        (isec.horizontal_wire_index, isec.vertical_wire_index)
        for isec in wire_result.intersections
    }
    missing_pairs = expected_pairs - detected_pairs

    for hi, vi in missing_pairs:
        if hi < len(wire_result.horizontal_wires) and vi < len(wire_result.vertical_wires):
            cx = int(round(wire_result.vertical_wires[vi].position_px))
            cy = int(round(wire_result.horizontal_wires[hi].position_px))
            color = np.array([0, 220, 255], dtype=np.float32)  # Yellow (Review)
            intensity = 0.85

            patch_r = int(sigma * 2.5)
            x0, x1 = max(0, cx - patch_r), min(w, cx + patch_r + 1)
            y0, y1 = max(0, cy - patch_r), min(h, cy + patch_r + 1)

            xs = np.arange(x0, x1) - cx
            ys = np.arange(y0, y1) - cy
            xx, yy = np.meshgrid(xs, ys)
            dist_sq = xx ** 2 + yy ** 2
            kernel = np.exp(-dist_sq / (2 * sigma ** 2)) * intensity

            for c in range(3):
                color_mask[y0:y1, x0:x1, c] += kernel * color[c]
            weight_mask[y0:y1, x0:x1] += kernel

    if rust_mask is not None:
        if rust_mask.shape[:2] != (h, w):
            rust_mask = cv2.resize(rust_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        rust_pixels = rust_mask > 0
        rust_color = np.array([0, 115, 255], dtype=np.float32)
        color_mask[rust_pixels] += rust_color
        weight_mask[rust_pixels] += 1.0

    # Normalize blended color
    nonzero = weight_mask > 0.001
    normalized_color = np.zeros_like(color_mask)
    for c in range(3):
        normalized_color[nonzero, c] = color_mask[nonzero, c] / weight_mask[nonzero]

    # Alpha blend onto base image
    blend_weights = np.clip(weight_mask, 0.0, 1.0) * alpha
    blended = base.astype(np.float32)
    for c in range(3):
        blended[:, :, c] = (
            blended[:, :, c] * (1.0 - blend_weights)
            + normalized_color[:, :, c] * blend_weights
        )
    output = np.clip(blended, 0, 255).astype(np.uint8)

    # Draw color-coded legend in bottom-left
    leg_x, leg_y = 16, h - 36
    cv2.rectangle(output, (leg_x - 6, leg_y - 20), (leg_x + 485, leg_y + 14), (20, 25, 35), -1)

    # Green box
    cv2.rectangle(output, (leg_x, leg_y - 12), (leg_x + 14, leg_y + 2), (40, 210, 40), -1)
    cv2.putText(output, "Normal", (leg_x + 20, leg_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    # Yellow box
    cv2.rectangle(output, (leg_x + 95, leg_y - 12), (leg_x + 109, leg_y + 2), (30, 210, 240), -1)
    cv2.putText(output, "Review / Uncertain", (leg_x + 115, leg_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    # Red box
    cv2.rectangle(output, (leg_x + 245, leg_y - 12), (leg_x + 259, leg_y + 2), (30, 30, 240), -1)
    cv2.putText(output, "Anomaly", (leg_x + 265, leg_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    # Amber box for rust-like surface discoloration
    cv2.rectangle(output, (leg_x + 340, leg_y - 12), (leg_x + 354, leg_y + 2), (0, 115, 255), -1)
    cv2.putText(output, "Rust-like", (leg_x + 360, leg_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

    # Header banner
    banner = "MESH + SURFACE OXIDATION HEATMAP (Visual Evidence)"
    cv2.rectangle(output, (0, 0), (w, 28), (20, 25, 35), -1)
    cv2.putText(output, banner, (12, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1, cv2.LINE_AA)

    return output


def draw_spacing_visualization(
    image: np.ndarray,
    spacing_result: MeshSpacingResult,
    wire_result: Optional[WireGridDetectionResult] = None,
) -> np.ndarray:
    """Wrapper around core.mesh_spacing.draw_mesh_spacing_overlay."""
    return draw_mesh_spacing_overlay(image, spacing_result, wire_result)
