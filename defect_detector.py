import cv2
import numpy as np
from PIL import Image
import io
import base64
import os

class WireMeshDefectDetector:
    """
    AI & Computer Vision Defect Detection Engine for Finished Wire Mesh Products.
    Detects:
    1. Severe Surface Rust / Corrosion
    2. Wire Bending / Grid Distortion / Non-parallel alignment
    3. Cut End Anomalies / Structural Irregularities
    4. Surface Anomaly Density & Heatmap
    """
    
    def __init__(self, rust_threshold=0.03, bend_threshold=8.0):
        self.rust_threshold = rust_threshold
        self.bend_threshold = bend_threshold

    def inspect_image(self, image_input):
        """
        Main inspection entrypoint.
        image_input: path (str), PIL.Image, or numpy.ndarray (BGR)
        Returns dictionary with detailed metrics, defect list, pass/fail status, and annotated images.
        """
        # Load image into numpy BGR array
        if isinstance(image_input, str):
            img_bgr = cv2.imread(image_input)
            filename = os.path.basename(image_input)
        elif isinstance(image_input, Image.Image):
            img_bgr = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            filename = "uploaded_image.jpg"
        elif isinstance(image_input, np.ndarray):
            img_bgr = image_input.copy()
            filename = "frame.jpg"
        else:
            raise ValueError("Unsupported image input type")

        if img_bgr is None:
            raise ValueError("Could not read image data")

        # Normalize resolution for consistent performance (max 1024 width/height)
        h, w = img_bgr.shape[:2]
        max_dim = 1024
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = img_bgr.shape[:2]

        # Convert to HSV and Gray
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        defects = []
        annotated = img_bgr.copy()
        total_pixels = h * w
        
        # -------------------------------------------------------------
        # 1. RUST / CORROSION DETECTION
        # -------------------------------------------------------------
        # Rust HSV ranges (reddish brown, orange, rust yellow)
        # Saturation minimum (S >= 70) avoids false positives on human skin tones and warm room lighting
        lower_rust1 = np.array([0, 70, 45])
        upper_rust1 = np.array([22, 255, 220])
        lower_rust2 = np.array([155, 70, 45])
        upper_rust2 = np.array([179, 255, 220])
        
        mask_rust1 = cv2.inRange(hsv, lower_rust1, upper_rust1)
        mask_rust2 = cv2.inRange(hsv, lower_rust2, upper_rust2)
        rust_mask = cv2.bitwise_or(mask_rust1, mask_rust2)
        
        # Clean up mask with morphological closing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        rust_mask_clean = cv2.morphologyEx(rust_mask, cv2.MORPH_CLOSE, kernel)
        
        # Blur and Canny edge detection (prepared early for texture verification)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150, apertureSize=3)

        # Find rust defect contours
        contours, _ = cv2.findContours(rust_mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        rust_regions = []
        valid_rust_pixels = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > max(35.0, total_pixels * 0.0015): # filter noise
                x, y, bw, bh = cv2.boundingRect(cnt)
                # Verify edge texture within region to rule out flat smooth surfaces like skin or painted background
                roi_edges = edges[y:y+bh, x:x+bw]
                if np.count_nonzero(roi_edges) >= 3 or area > (total_pixels * 0.01):
                    valid_rust_pixels += area
                    rust_regions.append({
                        "x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
                        "area": int(area),
                        "severity": "CRITICAL" if area > (total_pixels * 0.02) else "MAJOR" if area > (total_pixels * 0.005) else "MINOR"
                    })
                    # Draw bounding box for rust
                    color = (0, 0, 230) if area > (total_pixels * 0.02) else (0, 140, 255)
                    cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 2)
                    cv2.putText(annotated, f"RUST ({int(area)}px)", (x, max(15, y - 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        rust_ratio = float(valid_rust_pixels) / float(total_pixels)

        if rust_ratio > 0.05:
            defects.append({
                "type": "Surface Oxidation / Rust",
                "severity": "CRITICAL" if rust_ratio > 0.15 else "MAJOR",
                "description": f"Extensive surface rust detected ({rust_ratio*100:.1f}% of surface area)",
                "confidence": min(0.99, round(0.70 + rust_ratio * 2.0, 2)),
                "regions_count": len(rust_regions)
            })
        elif rust_ratio > 0.01:
            defects.append({
                "type": "Minor Surface Oxidation",
                "severity": "MINOR",
                "description": f"Localized rust spots detected ({rust_ratio*100:.2f}% of surface area)",
                "confidence": round(0.65 + rust_ratio * 3.0, 2),
                "regions_count": len(rust_regions)
            })

        # -------------------------------------------------------------
        # 2. WIRE GRID & DEFORMATION / BENDING DETECTION
        # -------------------------------------------------------------
        # Detect lines using HoughLinesP
        min_line_len = int(min(w, h) * 0.22)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=75, minLineLength=min_line_len, maxLineGap=25)
        
        vertical_angles = []
        horizontal_angles = []
        bending_defects = []
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                
                # Normalize angle to -90 to +90
                if angle < -90:
                    angle += 180
                elif angle > 90:
                    angle -= 180
                
                # Distinguish vertical (~ 90 or -90 deg) vs horizontal (~ 0 deg)
                abs_angle = abs(angle)
                if abs_angle > 65: # near vertical
                    vertical_angles.append((angle, (x1, y1, x2, y2)))
                elif abs_angle < 25: # near horizontal
                    horizontal_angles.append((angle, (x1, y1, x2, y2)))

        # Convert vertical angles to tilt relative to 90 deg vertical axis
        # (e.g., 85 deg and -85 deg are both 5 deg off vertical, not 170 deg apart)
        vert_tilts = [(a[0] - 90.0 if a[0] > 0 else a[0] + 90.0) for a in vertical_angles]
        horiz_tilts = [a[0] for a in horizontal_angles]
        
        # Require at least 4 vertical or 4 horizontal lines to assert wire grid parallelism
        vert_std = float(np.std(vert_tilts)) if len(vert_tilts) >= 4 else 0.0
        horiz_std = float(np.std(horiz_tilts)) if len(horiz_tilts) >= 4 else 0.0
        
        # Check for bent/deformed lines
        if vert_std > self.bend_threshold or horiz_std > self.bend_threshold:
            max_dev = max(vert_std, horiz_std)
            defects.append({
                "type": "Wire Grid Deformation / Bending",
                "severity": "CRITICAL" if max_dev > 15.0 else "MAJOR",
                "description": f"Non-parallel wire grid alignment detected (Angular variance: {max_dev:.1f}°)",
                "confidence": min(0.98, round(0.75 + max_dev / 50.0, 2)),
                "regions_count": len(vertical_angles) + len(horizontal_angles)
            })

            # Highlight irregular lines
            mean_vert = np.mean(vert_tilts) if len(vert_tilts) > 0 else 0
            mean_horiz = np.mean(horiz_tilts) if len(horiz_tilts) > 0 else 0

            for angle, (x1, y1, x2, y2) in vertical_angles + horizontal_angles:
                tilt = (angle - 90.0 if angle > 0 else angle + 90.0) if abs(angle) > 65 else angle
                ref_mean = mean_vert if abs(angle) > 65 else mean_horiz
                if abs(tilt - ref_mean) > 6.0:
                    cv2.line(annotated, (x1, y1), (x2, y2), (255, 0, 255), 3)
                    cv2.putText(annotated, "BENT WIRE", (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

        # -------------------------------------------------------------
        # 3. CUT END & EDGE INTEGRITY INSPECTION
        # -------------------------------------------------------------
        # Check border areas for irregular, frayed, or broken wire ends
        border_margin = int(min(w, h) * 0.08)
        border_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.rectangle(border_mask, (0, 0), (w, h), 255, -1)
        cv2.rectangle(border_mask, (border_margin, border_margin), (w - border_margin, h - border_margin), 0, -1)

        border_edges = cv2.bitwise_and(edges, edges, mask=border_mask)
        border_edge_pixels = np.count_nonzero(border_edges)
        border_edge_ratio = float(border_edge_pixels) / float(w * border_margin * 4)

        if border_edge_ratio > 0.08:
            defects.append({
                "type": "Irregular Wire Cut Ends",
                "severity": "MINOR",
                "description": "Exposed protrusion or uneven cut ends detected near mesh boundary",
                "confidence": round(0.72 + border_edge_ratio, 2),
                "regions_count": 1
            })

        # -------------------------------------------------------------
        # 4. GENERATE HEATMAP & OVERLAYS
        # -------------------------------------------------------------
        # Heatmap combines rust mask intensity and edge density anomaly
        edge_density = cv2.GaussianBlur(edges, (21, 21), 0)
        heatmap_gray = cv2.addWeighted(rust_mask_clean, 0.7, edge_density, 0.3, 0)
        heatmap_color = cv2.applyColorMap(heatmap_gray, cv2.COLORMAP_JET)
        heatmap_overlay = cv2.addWeighted(img_bgr, 0.6, heatmap_color, 0.4, 0)

        # -------------------------------------------------------------
        # 5. OVERALL QUALITY SCORE & VERDICT
        # -------------------------------------------------------------
        # Calculate quality score out of 100
        quality_score = 100.0
        
        # Deductions
        rust_deduction = min(50.0, rust_ratio * 250.0) # 10% rust = -25 points
        grid_deduction = min(35.0, (vert_std + horiz_std) * 2.0)
        edge_deduction = 10.0 if border_edge_ratio > 0.08 else 0.0
        
        quality_score = max(0.0, round(quality_score - rust_deduction - grid_deduction - edge_deduction, 1))

        if quality_score >= 85.0 and len(defects) == 0:
            verdict = "PASS"
        elif quality_score >= 65.0:
            verdict = "REWORK"
        else:
            verdict = "REJECT"

        # Add HUD overlay to annotated image
        cv2.rectangle(annotated, (10, 10), (320, 85), (20, 20, 20), -1)
        cv2.rectangle(annotated, (10, 10), (320, 85), (100, 100, 100), 1)
        
        v_color = (0, 220, 0) if verdict == "PASS" else (0, 220, 255) if verdict == "REWORK" else (0, 0, 255)
        cv2.putText(annotated, f"VERDICT: {verdict}", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, v_color, 2, cv2.LINE_AA)
        cv2.putText(annotated, f"QUALITY SCORE: {quality_score}%", (20, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1, cv2.LINE_AA)
        cv2.putText(annotated, f"DEFECTS FOUND: {len(defects)}", (20, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

        # Convert images to base64 JPEG for API / UI display
        _, buf_annotated = cv2.imencode('.jpg', annotated)
        b64_annotated = base64.b64encode(buf_annotated).decode('utf-8')

        _, buf_heatmap = cv2.imencode('.jpg', heatmap_overlay)
        b64_heatmap = base64.b64encode(buf_heatmap).decode('utf-8')

        return {
            "filename": filename,
            "verdict": verdict,
            "quality_score": quality_score,
            "defects": defects,
            "metrics": {
                "rust_area_percentage": round(rust_ratio * 100, 2),
                "grid_parallelism_dev_deg": round(float(max(vert_std, horiz_std)), 2),
                "total_wire_lines_detected": len(vertical_angles) + len(horizontal_angles),
                "rust_regions_count": len(rust_regions),
                "resolution": f"{w}x{h}"
            },
            "images": {
                "annotated_b64": f"data:image/jpeg;base64,{b64_annotated}",
                "heatmap_b64": f"data:image/jpeg;base64,{b64_heatmap}"
            }
        }

if __name__ == "__main__":
    import sys
    detector = WireMeshDefectDetector()
    sample_path = r"d:\A1\a1zip\a1\IMG_20260916_131120.jpg"
    if os.path.exists(sample_path):
        result = detector.inspect_image(sample_path)
        print(f"Sample Test: {result['filename']}")
        print(f"Verdict: {result['verdict']} (Score: {result['quality_score']}%)")
        print(f"Defects: {len(result['defects'])}")
        for d in result['defects']:
            print(f"  - [{d['severity']}] {d['type']}: {d['description']}")
