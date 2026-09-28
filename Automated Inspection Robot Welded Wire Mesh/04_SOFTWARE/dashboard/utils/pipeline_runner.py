"""
Unified Inspection Pipeline Runner for the A1 Mesh Inspection Dashboard.

Executes the complete deterministic inspection engine:
  IMAGE INPUT
      ↓
  IMAGE PREPROCESSING (core.preprocessing)
      ↓
  WIRE / GRID DETECTION (core.wire_detection)
      ↓
  INTERSECTION / WELD-REGION ANALYSIS (core.weld_intersection)
      ↓
  MESH SPACING MEASUREMENT (core.mesh_spacing)
      ↓
  VISION-BASED ANOMALY AGGREGATION
      ↓
  INSPECTION DECISION LOGIC (core.inspection_decision)
      ↓
  CLASSIFICATION: OK / SPACING DEFECT / WELD DEFECT / MULTIPLE DEFECTS / REVIEW

Does NOT duplicate algorithms; calls the existing working core modules directly.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

from config.settings import (
    CALIBRATION_CAVEAT_PROVISIONAL,
    CALIBRATION_CAVEAT_UNVALIDATED_ESTIMATE,
    DATA_PROCESSED_DIR,
)
from core.image_loader import ImageInfo, load_image
from core.inspection_decision import InspectionDecision, make_inspection_decision
from core.mesh_spacing import (
    STANDARD_PROFILES,
    MeshSpacingResult,
    ProductSpacingProfile,
    measure_mesh_spacing,
)
from core.preprocessing import PreprocessingResult, preprocess_image
from core.weld_intersection import WeldIntersectionResult, analyze_intersections
from core.wire_detection import WireGridDetectionResult, detect_wire_grid
from dashboard.utils.visualizations import (
    draw_anomaly_heatmap,
    draw_grid_overlay,
    draw_intersection_overlay,
    draw_spacing_visualization,
)


@dataclass
class AnomalyItem:
    """One factual, evidence-backed visual anomaly or review item."""
    id: int
    category: str
    location: str
    evidence: str
    status: str
    coordinates_px: Optional[Tuple[float, float]] = None


@dataclass
class PipelineInspectionResult:
    """Complete, self-contained record of an inspection run."""
    inspection_id: str
    timestamp: str
    source_name: str
    input_source_type: str  # "UPLOAD", "WEBCAM", "NETWORK_CAMERA"
    original_image: np.ndarray
    image_info: ImageInfo
    preprocessing_result: PreprocessingResult
    grayscale_image: np.ndarray
    edge_image: np.ndarray
    wire_result: WireGridDetectionResult
    weld_result: WeldIntersectionResult
    spacing_result: MeshSpacingResult
    decision: InspectionDecision
    final_classification: str  # "OK", "REVIEW", "SPACING DEFECT", "WELD DEFECT", "MULTIPLE DEFECTS"
    anomalies: List[AnomalyItem] = field(default_factory=list)
    # Overlays
    grid_overlay: Optional[np.ndarray] = None
    intersection_overlay: Optional[np.ndarray] = None
    heatmap_overlay: Optional[np.ndarray] = None
    spacing_overlay: Optional[np.ndarray] = None
    rust_area_percentage: float = 0.0
    rust_regions_count: int = 0
    rust_mask: Optional[np.ndarray] = None


class ClassificationInvariantError(RuntimeError):
    """Raised when determine_final_classification() reaches a combination of
    decision fields that the current 5-state taxonomy (OK / SPACING DEFECT /
    WELD DEFECT / MULTIPLE DEFECTS / REVIEW) cannot honestly classify.

    This is a development-time safety net, not an expected runtime path: per
    core.inspection_decision's own logic, final_status == "FAIL" can only be
    set when a spacing tolerance was actually violated (spacing_status ==
    "OUT_OF_TOLERANCE"), so spacing_fail is always True whenever this function
    is asked to classify a FAIL. If this error fires, a change to the FAIL-
    producing logic has broken that invariant - do NOT silently fall back to
    REVIEW, since that would mask a real, undocumented failure mode.
    """


def detect_surface_oxidation(image: np.ndarray) -> Tuple[np.ndarray, float, int]:
    """Estimate rust-like visible surface discoloration from HSV color and edges."""
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        bgr = image

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lower_rust = cv2.inRange(hsv, np.array([0, 70, 45]), np.array([22, 255, 220]))
    upper_rust = cv2.inRange(hsv, np.array([155, 70, 45]), np.array([179, 255, 220]))
    rust_mask = cv2.bitwise_or(lower_rust, upper_rust)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    rust_mask = cv2.morphologyEx(rust_mask, cv2.MORPH_CLOSE, kernel)

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150, apertureSize=3)
    contours, _ = cv2.findContours(rust_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid_mask = np.zeros(rust_mask.shape, dtype=np.uint8)
    region_count = 0
    min_area = max(35.0, image.shape[0] * image.shape[1] * 0.0015)

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue
        x, y, width, height = cv2.boundingRect(contour)
        if np.count_nonzero(edges[y:y + height, x:x + width]) < 3 and area <= image.shape[0] * image.shape[1] * 0.01:
            continue
        cv2.drawContours(valid_mask, [contour], -1, 255, thickness=cv2.FILLED)
        region_count += 1

    rust_area_percentage = float(np.count_nonzero(valid_mask)) / valid_mask.size * 100.0
    return valid_mask, round(rust_area_percentage, 2), region_count


def determine_final_classification(
    decision: InspectionDecision,
    spacing_result: MeshSpacingResult,
    weld_result: WeldIntersectionResult,
) -> str:
    """Map inspection decision and evidence to the 5 required dashboard categories.

    Rules per specification:
      - OK: Only when required evidence is complete, calibrated, within validated tolerance,
            and no confirmed anomaly exists.
      - SPACING DEFECT: Only when a calibrated spacing measurement violates a validated tolerance.
      - WELD DEFECT: Only when reliable evidence confirms a weld defect.
      - MULTIPLE DEFECTS: Multiple confirmed defect categories.
      - REVIEW: When evidence is incomplete, provisional, uncalibrated, anomalous but unconfirmed,
                or tolerance is not configured.

    These are the only 5 user-facing classification states. There is no sixth
    state: if evidence cannot be mapped to one of the 5 above, this function
    raises ClassificationInvariantError rather than inventing one.
    """
    if decision.final_status == "FAIL":
        spacing_fail = decision.spacing_status == "OUT_OF_TOLERANCE"
        weld_fail = False  # The system deliberately does NOT confirm weld mechanical failures
        if spacing_fail and weld_fail:
            return "MULTIPLE DEFECTS"
        elif spacing_fail:
            return "SPACING DEFECT"
        elif weld_fail:
            return "WELD DEFECT"
        raise ClassificationInvariantError(
            "final_status is FAIL but neither spacing_fail nor weld_fail is True "
            f"(spacing_status={decision.spacing_status!r}). This combination should "
            "be impossible under core.inspection_decision's current logic - FAIL "
            "must not silently be reported as REVIEW or any other state."
        )

    if decision.final_status == "PASS":
        return "OK"

    # Default conservative classification
    return "REVIEW"


def extract_real_anomalies(
    wire_result: WireGridDetectionResult,
    weld_result: WeldIntersectionResult,
    spacing_result: MeshSpacingResult,
) -> List[AnomalyItem]:
    """Compile real optical and geometric evidence into an itemized anomaly list.

    Does NOT generate random locations or fake ML scores. Uses strictly real data:
      - Potential intersection arm mismatches (core.weld_intersection)
      - Missing expected wire intersections (core.wire_detection)
      - Uncalibrated / provisional measurement zones (core.mesh_spacing)
    """
    items: List[AnomalyItem] = []
    item_id = 1

    # 1. Intersection visual arm mismatches
    for a in weld_result.assessments:
        if a.status == "POTENTIALLY_ANOMALOUS":
            items.append(AnomalyItem(
                id=item_id,
                category="Intersection Visual Arm Mismatch",
                location=f"Wire crossing H{a.horizontal_wire_index} - V{a.vertical_wire_index}",
                evidence=a.notes,
                status="POTENTIALLY_ANOMALOUS",
                coordinates_px=(round(a.x_px, 1), round(a.y_px, 1)),
            ))
            item_id += 1
        elif a.status == "INSUFFICIENT_EVIDENCE":
            items.append(AnomalyItem(
                id=item_id,
                category="Insufficient Visual Evidence",
                location=f"Wire crossing H{a.horizontal_wire_index} - V{a.vertical_wire_index}",
                evidence=a.notes,
                status="INSUFFICIENT_EVIDENCE",
                coordinates_px=(round(a.x_px, 1), round(a.y_px, 1)),
            ))
            item_id += 1

    # 2. Missing expected intersections (completeness < 1.0)
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

    for hi, vi in sorted(missing_pairs):
        if hi < len(wire_result.horizontal_wires) and vi < len(wire_result.vertical_wires):
            cx = wire_result.vertical_wires[vi].position_px
            cy = wire_result.horizontal_wires[hi].position_px
            items.append(AnomalyItem(
                id=item_id,
                category="Incomplete Grid Intersection",
                location=f"Expected crossing H{hi} - V{vi}",
                evidence="Horizontal and vertical wire extents did not detectably overlap at crossing.",
                status="REVIEW",
                coordinates_px=(round(cx, 1), round(cy, 1)),
            ))
            item_id += 1

    # 3. Spacing status limitations
    if any(s.calibration_status == "UNCALIBRATED" for s in spacing_result.horizontal_spacings):
        items.append(AnomalyItem(
            id=item_id,
            category="Calibration Limitation",
            location="Horizontal Axis Spacings",
            evidence="Horizontal scale uncalibrated due to documented position-dependent distortion; pixel spacing only.",
            status="UNCALIBRATED",
            coordinates_px=None,
        ))
        item_id += 1

    if any(s.calibration_status in ("PROVISIONAL", "UNVALIDATED ESTIMATE") for s in spacing_result.vertical_spacings):
        vert_cal_status = next(
            s.calibration_status for s in spacing_result.vertical_spacings
            if s.calibration_status in ("PROVISIONAL", "UNVALIDATED ESTIMATE")
        )
        if vert_cal_status == "UNVALIDATED ESTIMATE":
            evidence_text = CALIBRATION_CAVEAT_UNVALIDATED_ESTIMATE
        else:
            evidence_text = CALIBRATION_CAVEAT_PROVISIONAL
        items.append(AnomalyItem(
            id=item_id,
            category="Calibration Caveat",
            location="Vertical Axis Spacings",
            evidence=evidence_text,
            status=vert_cal_status,
            coordinates_px=None,
        ))
        item_id += 1

    return items


def run_inspection_pipeline(
    image_input: Union[str, Path, np.ndarray],
    source_name: str = "inspection_image.jpg",
    input_source_type: str = "UPLOAD",
    profile: Optional[ProductSpacingProfile] = None,
) -> PipelineInspectionResult:
    """Execute the full inspection pipeline on an image path or array.

    Args:
        image_input: File path (str/Path) or numpy BGR array.
        source_name: Name of the image for reporting.
        input_source_type: "UPLOAD", "WEBCAM", or "NETWORK_CAMERA".
        profile: Configurable ProductSpacingProfile (defaults to P001 Kavach).

    Returns:
        PipelineInspectionResult containing all data, metrics, and visual overlays.
    """
    if profile is None:
        profile = STANDARD_PROFILES.get("P001")

    now = datetime.now()
    inspection_id = f"INSP-{now.strftime('%Y%m%d-%H%M%S')}"
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: Load image and acquire basic properties
    if isinstance(image_input, (str, Path)):
        img_path = Path(image_input)
        original_image, image_info = load_image(img_path)
        actual_name = img_path.name
    elif isinstance(image_input, np.ndarray):
        original_image = image_input
        h, w = original_image.shape[:2]
        ch = original_image.shape[2] if original_image.ndim == 3 else 1
        image_info = ImageInfo(
            path=Path(source_name),
            width=w,
            height=h,
            channels=ch,
            file_format="jpg",
            file_size_bytes=int(original_image.nbytes),
        )
        actual_name = source_name
    else:
        raise ValueError(f"Unsupported image_input type: {type(image_input)}")

    rust_mask, rust_area_percentage, rust_regions_count = detect_surface_oxidation(original_image)

    # Step 2: Preprocessing
    prep_res = preprocess_image(
        image=original_image,
        source_name=actual_name,
        output_dir=DATA_PROCESSED_DIR,
        save_intermediate=True,
    )

    # Read preprocessed single-channel outputs
    edge_img = cv2.imread(str(prep_res.output_paths["edges"]), cv2.IMREAD_GRAYSCALE)
    gray_img = cv2.imread(str(prep_res.output_paths["grayscale"]), cv2.IMREAD_GRAYSCALE)

    # Step 3: Wire & Grid Detection
    wire_res = detect_wire_grid(edge_img, actual_name)

    # Step 4: Intersection / Weld-Region Appearance Analysis
    weld_res = analyze_intersections(gray_img, wire_res)

    # Step 5: Mesh Spacing Measurement
    spacing_res = measure_mesh_spacing(wire_res)

    # Step 6: Evidence-Based Inspection Decision
    decision = make_inspection_decision(
        wire_result=wire_res,
        weld_result=weld_res,
        spacing_result=spacing_res,
        profile=profile,
        source_name=actual_name,
    )

    # Step 7: Final 5-state Classification Mapping
    final_classification = determine_final_classification(decision, spacing_res, weld_res)

    # Step 8: Itemized Real Anomalies
    anomalies = extract_real_anomalies(wire_res, weld_res, spacing_res)

    # Step 9: Render Visual Inspection Overlays
    grid_overlay = draw_grid_overlay(gray_img, wire_res)
    intersection_overlay = draw_intersection_overlay(gray_img, wire_res, weld_res)
    heatmap_overlay = draw_anomaly_heatmap(
        gray_img, wire_res, weld_res, spacing_res, rust_mask=rust_mask
    )
    spacing_overlay = draw_spacing_visualization(gray_img, spacing_res, wire_res)

    return PipelineInspectionResult(
        inspection_id=inspection_id,
        timestamp=timestamp_str,
        source_name=actual_name,
        input_source_type=input_source_type,
        original_image=original_image,
        image_info=image_info,
        preprocessing_result=prep_res,
        grayscale_image=gray_img,
        edge_image=edge_img,
        wire_result=wire_res,
        weld_result=weld_res,
        spacing_result=spacing_res,
        decision=decision,
        final_classification=final_classification,
        anomalies=anomalies,
        grid_overlay=grid_overlay,
        intersection_overlay=intersection_overlay,
        heatmap_overlay=heatmap_overlay,
        spacing_overlay=spacing_overlay,
        rust_area_percentage=rust_area_percentage,
        rust_regions_count=rust_regions_count,
        rust_mask=rust_mask,
    )
