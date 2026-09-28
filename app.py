import os
import io
import sys
import time
import base64
import json
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from PIL import Image
import numpy as np
import cv2

# Add 04_SOFTWARE to path for core inspection engine
SOFTWARE_PATH = os.path.join(os.path.dirname(__file__), 'Automated Inspection Robot Welded Wire Mesh', '04_SOFTWARE')
if SOFTWARE_PATH not in sys.path:
    sys.path.insert(0, SOFTWARE_PATH)

from dashboard.utils.pipeline_runner import run_inspection_pipeline, STANDARD_PROFILES
from dashboard.utils.presentation import (
    inspection_view_model,
    visual_mode_evidence,
    finding_rows,
    spacing_rows,
    calibration_rows,
    finding_counts,
    evidence_statements,
    limitation_rows
)

app = Flask(__name__, static_folder='dist', static_url_path='')
CORS(app)

DATASET_DIR = os.path.join(os.path.dirname(__file__), 'a1zip', 'a1')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'inspection_results', 'inspection_history.json')

def load_inspection_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as history_file:
            records = json.load(history_file)
        return [record for record in records if isinstance(record, dict)] if isinstance(records, list) else []
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        app.logger.error('Could not load inspection history: %s', error)
        return []


def save_inspection_history():
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    temporary_file = HISTORY_FILE + '.tmp'
    with open(temporary_file, 'w', encoding='utf-8') as history_file:
        json.dump(inspection_history, history_file, indent=2)
    os.replace(temporary_file, HISTORY_FILE)


inspection_history_lock = threading.RLock()
inspection_history = load_inspection_history()

def bgr_to_b64(img_bgr, quality=85):
    if img_bgr is None:
        return None
    success, buffer = cv2.imencode('.jpg', img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        return None
    return f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

def process_pipeline_result(pipeline_res, profile_id='P001', elapsed_ms=0.0):
    vm = inspection_view_model(pipeline_res)
    
    # Generate base64 overlays for all 5 visualization modes
    original_b64 = bgr_to_b64(pipeline_res.original_image)
    grid_b64 = bgr_to_b64(pipeline_res.grid_overlay) or original_b64
    intersection_b64 = bgr_to_b64(pipeline_res.intersection_overlay) or original_b64
    heatmap_b64 = bgr_to_b64(pipeline_res.heatmap_overlay) or original_b64
    spacing_b64 = bgr_to_b64(pipeline_res.spacing_overlay) or original_b64
    
    evidence_by_mode = {
        'ORIGINAL': visual_mode_evidence(pipeline_res, 'ORIGINAL'),
        'GRID': visual_mode_evidence(pipeline_res, 'GRID'),
        'INTERSECTIONS': visual_mode_evidence(pipeline_res, 'INTERSECTIONS'),
        'HEATMAP': visual_mode_evidence(pipeline_res, 'HEATMAP'),
        'SPACING': visual_mode_evidence(pipeline_res, 'SPACING'),
    }

    # Extract weld defect metrics
    weld_res = pipeline_res.weld_result
    wire_res = pipeline_res.wire_result

    missing_welds_count = max(0, wire_res.expected_intersections - wire_res.num_intersections)
    irregular_welds_count = weld_res.num_potentially_anomalous
    normal_welds_count = weld_res.num_normal

    # Extract wire deformation metrics
    angle_h_dev = float(vm.get("angle_h", "0").replace("°", "").strip() or 0)
    angle_v_dev = float(vm.get("angle_v", "0").replace("°", "").strip() or 0)
    max_grid_dev = max(angle_h_dev, angle_v_dev)

    bent_wires_count = 1 if max_grid_dev > 8.0 else 0
    broken_wires_count = missing_welds_count  # Missing junctions indicate broken or cut wire extents

    # Automatic Inspection Decision Logic
    decision_reasons = []
    passed_checks = []

    # Check 1: Weld Integrity
    if missing_welds_count > 0:
        decision_reasons.append(f"Incomplete grid welding: {missing_welds_count} missing junction crossing(s) detected.")
    elif irregular_welds_count > 0:
        decision_reasons.append(f"{irregular_welds_count} weld junction(s) show visual arm mismatch requiring review.")
    else:
        passed_checks.append(f"All {wire_res.num_intersections} expected weld junctions present and normal.")

    # Check 2: Wire Deformation & Bending
    if max_grid_dev > 15.0:
        decision_reasons.append(f"Critical wire bending deformation: Angular deviation {max_grid_dev:.2f}° exceeds 15° threshold.")
    elif max_grid_dev > 8.0:
        decision_reasons.append(f"Wire grid non-parallel alignment: Angular deviation {max_grid_dev:.2f}° exceeds 8° tolerance.")
    else:
        passed_checks.append(f"Wire alignment parallel within tolerance ({max_grid_dev:.2f}° dev).")

    # Classification & Verdict Determination
    if max_grid_dev > 15.0 or missing_welds_count > 2:
        verdict = "FAIL"
        classification = "FAIL - DEFECT DETECTED"
        quality_score = max(0.0, round(100.0 - (max_grid_dev * 2.5) - (missing_welds_count * 15.0), 1))
    elif missing_welds_count > 0 or irregular_welds_count > 0 or max_grid_dev > 8.0:
        verdict = "REWORK"
        classification = "REVIEW - POTENTIAL ANOMALY"
        quality_score = max(50.0, round(100.0 - (max_grid_dev * 2.0) - (irregular_welds_count * 5.0) - (missing_welds_count * 10.0), 1))
    else:
        verdict = "PASS"
        classification = "PASS - CONFORMS TO QA STANDARD"
        quality_score = round(min(100.0, 95.0 + (wire_res.intersection_completeness * 5.0)), 1)
        passed_checks.append("All physical pitch and weld integrity parameters conform to nominal specifications.")

    # Format structured defects list
    structured_defects = []
    if missing_welds_count > 0:
        structured_defects.append({
            "category": "Missing / Incomplete Weld",
            "severity": "CRITICAL" if missing_welds_count > 2 else "MAJOR",
            "type": "Missing Weld Junction",
            "description": f"{missing_welds_count} expected wire grid crossing(s) missing weld connection",
            "location": "Grid Intersections"
        })
    if irregular_welds_count > 0:
        structured_defects.append({
            "category": "Weak / Irregular Weld",
            "severity": "MAJOR",
            "type": "Irregular Weld Appearance",
            "description": f"{irregular_welds_count} weld region(s) show visual arm width mismatch requiring review",
            "location": "Weld Junctions"
        })
    if bent_wires_count > 0:
        structured_defects.append({
            "category": "Bent / Deformed Wire",
            "severity": "CRITICAL" if max_grid_dev > 15.0 else "MAJOR",
            "type": "Wire Grid Bending",
            "description": f"Non-parallel wire alignment detected with {max_grid_dev:.2f}° angular variance",
            "location": "Wire Grid Span"
        })
    if broken_wires_count > 0:
        structured_defects.append({
            "category": "Broken Wire / Cut End Anomaly",
            "severity": "MAJOR",
            "type": "Unconnected Wire Extent",
            "description": "Wire end protrusion or incomplete extent near grid boundary",
            "location": "Mesh Boundary"
        })

    # Compile payload
    payload = {
        "inspection_id": pipeline_res.inspection_id,
        "timestamp": pipeline_res.timestamp,
        "filename": pipeline_res.source_name,
        "classification": classification,
        "verdict": verdict,
        "quality_score": quality_score,
        "latency_ms": elapsed_ms,
        "view_model": vm,
        "evidence_by_mode": evidence_by_mode,
        "images": {
            "ORIGINAL": original_b64,
            "GRID": grid_b64,
            "INTERSECTIONS": intersection_b64,
            "HEATMAP": heatmap_b64,
            "SPACING": spacing_b64,
            "annotated_b64": grid_b64,
            "heatmap_b64": heatmap_b64
        },
        "weld_analysis": {
            "missing_welds_count": missing_welds_count,
            "irregular_welds_count": irregular_welds_count,
            "normal_welds_count": normal_welds_count,
            "expected_intersections": wire_res.expected_intersections,
            "status": "FAIL" if missing_welds_count > 2 else "REVIEW" if (missing_welds_count > 0 or irregular_welds_count > 0) else "PASS"
        },
        "wire_analysis": {
            "bent_wires_count": bent_wires_count,
            "broken_wires_count": broken_wires_count,
            "grid_parallelism_dev_deg": max_grid_dev,
            "num_horizontal": wire_res.num_horizontal_wires,
            "num_vertical": wire_res.num_vertical_wires,
            "status": "FAIL" if max_grid_dev > 15.0 else "REVIEW" if max_grid_dev > 8.0 else "PASS"
        },
        "automatic_decision": {
            "verdict": verdict,
            "classification": classification,
            "reasons": decision_reasons if decision_reasons else ["No quality deviations detected."],
            "passed_checks": passed_checks
        },
        "metrics": {
            "num_horizontal": vm.get("num_horizontal", 0),
            "num_vertical": vm.get("num_vertical", 0),
            "num_intersections": vm.get("num_intersections", 0),
            "expected_intersections": vm.get("expected_intersections", 0),
            "completeness": vm.get("completeness", "100%"),
            "grid_parallelism_dev_deg": max_grid_dev,
            "total_wire_lines_detected": wire_res.num_horizontal_wires + wire_res.num_vertical_wires,
            "potential_anomalies": vm.get("potential_anomalies", 0),
            "resolution": f"{vm.get('image_width', 0)}x{vm.get('image_height', 0)}"
        },
        "defects": structured_defects
    }

    # Record metrics history
    with inspection_history_lock:
        inspection_history.append({
            "inspection_id": pipeline_res.inspection_id,
            "timestamp": pipeline_res.timestamp,
            "filename": pipeline_res.source_name,
            "profile_id": profile_id,
            "verdict": verdict,
            "classification": classification,
            "quality_score": quality_score,
            "defects_count": len(structured_defects),
            "latency_ms": elapsed_ms
        })
        save_inspection_history()

    return payload

@app.route('/api/dataset', methods=['GET'])
def get_dataset():
    """Returns list of available sample images from workspace dataset"""
    if not os.path.exists(DATASET_DIR):
        return jsonify({"error": "Dataset directory not found"}), 404
    
    files = [f for f in os.listdir(DATASET_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    return jsonify({
        "total_images": len(files),
        "files": files[:30] # list top 30 sample images
    })

@app.route('/api/dataset_image/<filename>', methods=['GET'])
def serve_dataset_image(filename):
    """Serves raw image from dataset"""
    return send_from_directory(DATASET_DIR, filename)

@app.route('/api/inspect', methods=['POST'])
def inspect():
    """Accepts image upload or base64 stream and runs full inspection pipeline"""
    t0 = time.time()
    try:
        profile_id = request.form.get('profile_id', 'P001')
        profile = STANDARD_PROFILES.get(profile_id, STANDARD_PROFILES.get('P001'))

        if 'file' in request.files:
            file = request.files['file']
            file_bytes = np.frombuffer(file.read(), np.uint8)
            img_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            filename = file.filename
            input_source = "UPLOAD"
        elif request.is_json and 'image_b64' in request.json:
            b64_data = request.json['image_b64']
            profile_id = request.json.get('profile_id', 'P001')
            profile = STANDARD_PROFILES.get(profile_id, STANDARD_PROFILES.get('P001'))
            if ',' in b64_data:
                b64_data = b64_data.split(',')[1]
            img_data = base64.b64decode(b64_data)
            nparr = np.frombuffer(img_data, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            filename = request.json.get('filename', 'webcam_frame.jpg')
            input_source = "WEBCAM"
        else:
            return jsonify({"error": "No image file or image_b64 provided"}), 400

        pipeline_res = run_inspection_pipeline(
            image_input=img_bgr,
            source_name=filename,
            input_source_type=input_source,
            profile=profile
        )
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        result = process_pipeline_result(pipeline_res, profile_id, elapsed_ms)
        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/inspect_dataset_item', methods=['POST'])
def inspect_dataset_item():
    """Inspects a specific sample image from the local dataset by filename"""
    t0 = time.time()
    data = request.get_json() or {}
    filename = data.get('filename')
    profile_id = data.get('profile_id', 'P001')
    profile = STANDARD_PROFILES.get(profile_id, STANDARD_PROFILES.get('P001'))
    
    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    filepath = os.path.join(DATASET_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": f"File {filename} not found in dataset"}), 404

    try:
        pipeline_res = run_inspection_pipeline(
            image_input=filepath,
            source_name=filename,
            input_source_type="UPLOAD",
            profile=profile
        )
        elapsed_ms = round((time.time() - t0) * 1000, 1)
        result = process_pipeline_result(pipeline_res, profile_id, elapsed_ms)
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns aggregated inspection analytics"""
    with inspection_history_lock:
        records = list(inspection_history)
    total = len(records)
    if total == 0:
        return jsonify({
            "total_inspected": 0,
            "pass_rate": None,
            "pass_count": 0,
            "rework_count": 0,
            "reject_count": 0,
            "avg_quality_score": None,
            "avg_latency_ms": 0.0
        })

    pass_count = sum(1 for item in records if item.get("verdict") == "PASS")
    rework_count = sum(1 for item in records if item.get("verdict") in ("REWORK", "REVIEW"))
    reject_count = sum(1 for item in records if item.get("verdict") in ("REJECT", "FAIL"))
    avg_score = sum(item.get("quality_score", 0) for item in records) / total
    avg_latency = sum(item.get("latency_ms", 0) for item in records) / total

    return jsonify({
        "total_inspected": total,
        "pass_rate": round((pass_count / total) * 100, 1),
        "pass_count": pass_count,
        "rework_count": rework_count,
        "reject_count": reject_count,
        "avg_quality_score": round(avg_score, 1),
        "avg_latency_ms": round(avg_latency, 1)
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    """Returns recent compact inspection records for analytics and traceability."""
    try:
        limit = max(1, min(int(request.args.get('n', 20)), 100))
    except ValueError:
        return jsonify({"error": "n must be an integer"}), 400

    with inspection_history_lock:
        records = list(inspection_history[-limit:])
    return jsonify({"history": records})

@app.route('/api/reset_stats', methods=['POST'])
def reset_stats():
    """Clears inspection history for a fresh session"""
    with inspection_history_lock:
        inspection_history.clear()
        save_inspection_history()
    return jsonify({"status": "ok", "message": "Inspection history cleared."})

@app.route('/')
def serve_index():
    if os.path.exists(os.path.join(app.static_folder, 'index.html')):
        return send_from_directory(app.static_folder, 'index.html')
    return "AI Manufacturing Defect Detection API Server Running."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
