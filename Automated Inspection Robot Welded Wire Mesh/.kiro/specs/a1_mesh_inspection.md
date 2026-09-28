# Feature Specification: A1 Mesh Inspection Prototype
**Revision:** 3 — OI-01 Resolved

**Project:** Automated Quality Inspection System for Welded Wire Mesh
**Team:** A1 Titans
**Workflow:** Requirements-First
**Status:** Awaiting Approval — No Implementation Until Confirmed

---

## Source of Truth

This specification is derived exclusively from:

- `00_MASTER/PROJECT_MASTER.md`
- `00_MASTER/A1_PRODUCT_SPECIFICATIONS.md`
- `00_MASTER/A1_SOURCE_REGISTER.md`
- `00_MASTER/PROJECT_SCOPE_AND_LIMITATIONS.md`
- `02_DATASET/DATASET_README.md`
- `02_DATASET/LABELING_RULES.md`

No requirement, tolerance, algorithm choice, or performance claim has been
invented beyond what these documents specify.

---

## Mandatory Engineering Constraints

These constraints are non-negotiable and apply to every module, every phase,
and every output of this system.

1. The representative dataset must never be described as confirmed A-1 Fence
   product material.

2. No PASS or FAIL acceptance decision may be produced without a formally
   validated tolerance. Without a validated tolerance the system must report
   the measured value and use the status NOT_CONFIGURED. The system does not
   invent thresholds.

3. Camera vision does not measure tensile strength, weld shear strength,
   coating thickness, coating adhesion, or salt-spray resistance. The system
   must never claim otherwise.

4. Computer vision identifies visible wire intersections and visually
   detectable missing or abnormal intersection regions. It does not determine
   weld strength or weld quality by mechanical means.

5. Product specifications must be stored as configurable profiles.
   No mesh geometry is hard-coded.

6. Original dataset images must never be modified. All processed outputs
   go to separate paths.

7. Simulated defects must always be labelled SIMULATED. Real defects REAL.
   Unknown status UNKNOWN. No label is invented without evidence.

8. Images from the same physical mesh sample must not be split across
   training and test sets.

9. Every major software module must be independently testable without
   requiring physical camera hardware.

10. No specific CV algorithm, ML model, or detection approach is mandated
    before the dataset audit is complete. Algorithm selection follows
    audit findings.

---

## Part 1 — Requirements

### 1.1 Functional Requirements

---

#### FR-01  Product Profile Management

The system shall store mesh product specifications as configurable profiles,
not as hard-coded constants.

The initial profiles are:

| Profile ID | Name                    | Wire Diameter (mm)   | Aperture (mm)         |
|------------|-------------------------|----------------------|-----------------------|
| P001       | Kavach / Anti-Climb 358 | 4.0 H & V            | 12.7 × 76.2           |
| P002       | Twin Wire Panels        | 8.0 H / 6.0 V        | 50.0 × 200.0          |
| P003       | UNICO Modular Fence     | 4.0 or 5.0           | 50.0 × 200.0 / custom |

Each profile stores: profile ID, name, nominal wire diameter(s), nominal mesh
aperture, applicable standards, corrosion protection type, and a tolerances
block that is null until formally validated.

The active profile must be selectable at runtime before an inspection begins.

No tolerance values are populated in any profile until they are formally
validated from authoritative A-1 product documentation.

For the UNICO profile, if a custom aperture is selected, the user must supply
the nominal aperture value at runtime. If no value is supplied, the nominal
reference fields in the inspection record are left null and no deviation
computation is performed.

---

#### FR-02  Camera Calibration

The system shall support a pixel-to-mm calibration procedure.

A physical reference target of known dimensions shall be placed on the same
plane as the mesh under inspection. Calibration is performed from this target.

The calibration result shall include a scale factor (pixels per mm) and an
estimate of the spatial error or confidence of that measurement.

The system shall validate calibration before accepting dimensional claims:
- The computed scale factor must be physically plausible given the camera and
  working distance in use.
- If perspective distortion is present and not fully corrected, the system
  must note that a single global pixels-per-mm value may not be uniformly
  valid across the full image. In that case, per-region or post-correction
  calibration shall be used.

If no valid calibration exists the system shall report measurements in pixels
only and label every such measurement explicitly as UNCALIBRATED.
The system shall not report millimetre values without a valid calibration.

---

#### FR-03  Image Acquisition

The system shall support two acquisition modes:

a) Live capture from a USB webcam connected to the host laptop.
b) File-based loading of an image from a file path, for dataset development
   and offline testing.

The system shall record the acquisition timestamp with every image.
The acquisition mode (webcam / file) shall be recorded in the inspection record.

---

#### FR-04  Image Preprocessing

The system shall apply a preprocessing pipeline to each acquired image before
geometric analysis. Preprocessing produces a working copy; the original image
file is never modified.

The preprocessing pipeline shall include at minimum:

- Grayscale conversion
- Noise reduction
- Contrast enhancement
- Perspective correction (homographic or affine transform where correction
  reference points are provided; identity transform if not provided, with a
  flag that correction was not applied)

The specific filter types and parameters for each step shall be externalised
in the pipeline configuration file, not hard-coded. They may be updated after
dataset audit without changing module interfaces.

---

#### FR-05  Wire Detection

The system shall detect horizontal and vertical wire lines in the preprocessed
image.

Wire detection shall produce:
- A set of detected horizontal wire positions (pixel coordinates)
- A set of detected vertical wire positions (pixel coordinates)
- An estimated wire width at each detected wire in pixels, and in mm if
  calibrated

The specific algorithm used for wire detection (e.g. Hough transform,
morphological skeleton, gradient-based) shall be selected after dataset audit
based on the image characteristics found in the dataset. The module interface
is fixed; the algorithm inside is replaceable.

---

#### FR-06  Intersection Detection

The system shall identify wire intersection locations (the points where
horizontal and vertical wires cross) using the wire positions detected in FR-05.

For each expected grid intersection the system shall record:
- The expected pixel location
- Whether a visually detectable intersection feature is present at that location
- A flag for missing or visually abnormal intersections

The system identifies visible intersections and visible absence of intersections.
It does not determine weld strength or mechanical weld quality.

The specific visual feature used to confirm an intersection (intensity, gradient,
morphology) shall be selected after dataset audit.

---

#### FR-07  Mesh Spacing Measurement

The system shall measure the spacing between adjacent detected wires in both
horizontal and vertical directions.

For each spacing the system shall record:
- Direction (horizontal or vertical)
- Measured spacing in pixels
- Measured spacing in mm (only if calibration is valid and calibration
  confidence is acceptable for the measurement region)
- The nominal spacing from the active product profile (displayed as a
  reference value, clearly labelled as nominal)
- The deviation from nominal (displayed as an informational value only;
  not a PASS/FAIL criterion unless a formally validated tolerance is present
  in the active profile)

---

#### FR-08  Wire Alignment Analysis

The system shall analyse the straightness of each detected wire.

For each wire the system shall report:
- The maximum lateral deviation from a fitted reference line (pixels and mm
  if calibrated)
- A display flag if the deviation exceeds a configurable display threshold
  (the threshold is for display purposes, not a PASS/FAIL criterion)

---

#### FR-09  Mesh Distortion Analysis

The system shall compute mesh distortion indicators from the detected wire grid:
- Variance of horizontal spacing values
- Variance of vertical spacing values
- Angular deviation of the wire grid from the horizontal/vertical reference
  (skew angle in degrees)

---

#### FR-10  Visual Anomaly Detection

The system shall detect candidate anomaly regions in the mesh image.

Detection shall operate in two stages:

Stage 1 — Candidate identification: detect image regions that deviate from
the expected regular mesh appearance. This produces a set of candidate regions
with bounding boxes. No category is assigned yet.

Stage 2 — Category assignment: assign a category to each candidate region
from the allowed label set:

  OK | SPACING_ANOMALY | WELD_INTERSECTION_ANOMALY |
  ALIGNMENT_DISTORTION | VISIBLE_SURFACE_ANOMALY | UNKNOWN

UNKNOWN shall be assigned whenever visual evidence is insufficient to support
a specific category. The system shall not assign a specific category by
inference or assumption.

The system shall not infer coating defects from images of an uncoated mesh.

The specific algorithm used for candidate detection (morphological, statistical,
learned) shall be selected after dataset audit based on image quality and
defect diversity found in the dataset.

---

#### FR-11  ML-Based Anomaly Classification (Conditional and Deferred)

ML-based classification is optional and may be added only after the dataset
audit has been completed and the following conditions have been assessed and
documented:

- Number of distinct physical samples available
- Total number of labelled images available
- Class distribution (images per category)
- Class diversity (visual variation within each category)
- Image quality consistency across the dataset
- Feasibility of a clean train/validation/test split with no cross-sample
  leakage

The decision on whether to proceed with ML, and the minimum data requirements
for doing so, shall be made at the conclusion of the dataset audit. No minimum
sample count is specified here in advance.

If ML is used:
- The model is a complement to deterministic detection, not a replacement.
- The result is labelled as an ML SUGGESTION, not a definitive inspection
  decision.
- Model performance metrics (precision, recall, F1 per class) must be recorded
  and disclosed.
- The train, validation, and test split must be verified to contain no images
  from the same physical sample.

If conditions are not met, this module is omitted entirely. Deterministic
detection alone is used.

---

#### FR-12  Defect and Anomaly Location Reporting

The system shall report the image-plane location of every detected anomaly
using a consistent coordinate convention.

Coordinate convention: origin (0, 0) at the top-left corner of the inspection
image; x increasing right; y increasing down; units in pixels, and in mm if
calibration is valid and spatially applicable.

---

#### FR-13  Inspection Result Status

Each inspection shall produce one of three result statuses:

- PASS: The measured values are within a formally validated tolerance range
  that is present in the active product profile.
- FAIL: One or more measured values fall outside a formally validated tolerance
  range that is present in the active product profile.
- NOT_CONFIGURED: No formally validated tolerance exists for this product
  profile. The measured values are reported for information. No acceptance
  decision is made.

In this prototype, all product profiles have `tolerances: null`. Therefore
the inspection status for all current inspections shall be NOT_CONFIGURED.
PASS or FAIL shall not appear in any output until validated tolerances have
been added to a profile by an authorised process.

---

#### FR-14  Inspection Record Output

For each inspection run the system shall produce a structured inspection record
containing:

- Inspection ID (auto-generated, unique per run)
- Timestamp
- Acquisition mode (webcam / file)
- Source image filename
- Dataset label: "DEVELOPMENT — Representative sample. Not confirmed A-1 Fence product."
- Active profile ID and name
- Calibration status (CALIBRATED / UNCALIBRATED), scale factor if calibrated,
  calibration confidence note
- Perspective correction applied (yes / no)
- Wire detection summary (H wire count, V wire count)
- Spacing measurements (all gap values, mean, std dev, nominal reference,
  deviations — all labelled as informational)
- Wire alignment summary (per-wire deviation)
- Intersection summary (expected count, detected count, missing count)
- Distortion metrics (spacing variance H and V, skew angle)
- Detected anomalies (bounding box, category, defect status, ML suggestion
  and confidence if applicable)
- Inspection result status: NOT_CONFIGURED (or PASS / FAIL when tolerances
  are validated and present)

The record shall be saved in both CSV and JSON formats to `outputs/records/`.

---

#### FR-15  Inspection Dashboard

The system shall display an inspection dashboard that shows all of the
following:

- The inspection image with detection overlays (detected wires, intersections,
  missing or abnormal intersections, anomaly bounding boxes with labels)
- The selected product profile name and ID
- Calibration status and scale factor
- All spacing measurements
- Anomaly list with location and category
- ML suggestion and confidence, if available
- Inspection ID
- Timestamp
- Inspection result status (NOT_CONFIGURED in all current runs)
- Link or path to the saved inspection record

The disclaimer must be visible on every dashboard screen:
"DEVELOPMENT DATASET — Representative sample. Not confirmed A-1 Fence product."

The dashboard technology (OpenCV window, Tkinter, web-based, or other) shall
be decided before the dashboard implementation phase begins, based on project
resources and demonstration requirements. The requirement here specifies
content only, not technology.

---

#### FR-16  Dataset Management Utilities

The system shall provide a dataset utility that:

- Assigns a unique sample ID to each distinct physical mesh sample
- Records the image filenames associated with each sample ID
- Writes a dataset manifest file (JSON) mapping sample IDs to images and labels
- Flags near-duplicate images for human review
- Provides a split-verification function: given a proposed train and test list,
  raises an error if any sample ID appears in both
- Records the dataset disclaimer label in the manifest

The manifest schema is described in the Design section.

---

#### FR-17  Dataset Audit (Mandatory Pre-Implementation Phase)

Before any CV algorithm implementation, ML work, or dashboard development
begins, a formal dataset audit must be completed.

The audit shall produce a written Dataset Audit Report covering:

- Total image count in the dataset
- Physical sample count and sample ID assignments
- Image format, resolution, and quality assessment
- Label distribution: count per category
  (OK / SPACING_ANOMALY / WELD_INTERSECTION_ANOMALY /
   ALIGNMENT_DISTORTION / VISIBLE_SURFACE_ANOMALY / UNKNOWN)
- Defect status distribution (REAL / SIMULATED / UNKNOWN)
- Near-duplicate image identification
- Cross-sample leakage risk assessment for any proposed train/test split
- ML feasibility decision: proceed / do not proceed, with justification
- Recommended CV algorithm candidates for wire detection and anomaly detection,
  based on observed image characteristics
- Any labelling corrections required under LABELING_RULES.md

The dataset audit is a gate. CV algorithm implementation, ML implementation,
and dashboard implementation do not begin until the audit report is accepted.

---

#### FR-18  Future ESP32 Integration (Architecture Stub)

The software architecture shall include a defined serial communication interface
for future ESP32-controlled indexed inspection.

In this prototype the interface is a stub module. It exposes the command API
but all methods return stub responses. No serial hardware is required to import
or run the module.

Future scope (out of this prototype): ESP32 sends position signals; the system
triggers capture at each indexed position; results accumulate into a panel-level
record.

---

### 1.2 Non-Functional Requirements

| ID     | Requirement |
|--------|-------------|
| NFR-01 | **Modularity.** Each pipeline stage is an independent importable module. No circular imports. Module interfaces are stable; internal algorithms are replaceable. |
| NFR-02 | **Testability.** Every module can be exercised by unit tests without physical camera hardware or an active ESP32. |
| NFR-03 | **Configurability.** All CV tuning parameters (filter types, thresholds, kernel sizes, algorithm selection flags) are defined in a pipeline configuration file. No magic numbers in source code. |
| NFR-04 | **Dataset Integrity.** No code path overwrites an original dataset image. All outputs are written to directories separate from the source dataset. |
| NFR-05 | **Honest Reporting.** Every output clearly distinguishes: calibrated mm values from uncalibrated pixel values; representative dataset from confirmed A-1 product; deterministic CV result from ML suggestion; measured value from nominal reference; NOT_CONFIGURED status from PASS or FAIL. |
| NFR-06 | **Performance Target (Prototype).** The full pipeline should process a single image in under 10 seconds on the development laptop for images up to 1920×1080. This is an indicative prototype target, not a validated SLA. It will be measured during implementation and revised if necessary. |
| NFR-07 | **Reproducibility.** Given the same input image and the same configuration, the pipeline produces the same output on every run (deterministic behaviour; no stochastic state in the CV pipeline). |
| NFR-08 | **Portability.** The software runs on Windows (current development environment). Dependencies are managed via `requirements.txt` with pinned versions. |
| NFR-09 | **Algorithm Replaceability.** Wire detection, intersection detection, and anomaly detection algorithm choices are encapsulated inside their respective modules. Changing the algorithm requires only changes inside the module, not changes to calling code or data schemas. |

---

## Part 2 — Design

### 2.1 Repository Structure

```
04_SOFTWARE/
│
├── config/
│   ├── product_profiles.json       # A-1 product profile definitions
│   └── pipeline_config.json        # CV pipeline parameters (algorithm flags + tuning)
│
├── src/
│   ├── acquisition/
│   │   ├── __init__.py
│   │   ├── camera.py               # USB webcam capture
│   │   └── file_loader.py          # Load images from file path
│   │
│   ├── calibration/
│   │   ├── __init__.py
│   │   └── calibrator.py           # Pixel-to-mm calibration + validation
│   │
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   └── preprocessor.py         # Grayscale, denoise, contrast, perspective
│   │
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── wire_detector.py        # Wire line detection (algorithm selectable)
│   │   ├── intersection_detector.py # Visible intersection analysis
│   │   └── anomaly_detector.py     # Candidate anomaly detection (algorithm selectable)
│   │
│   ├── measurement/
│   │   ├── __init__.py
│   │   ├── spacing.py              # Mesh spacing measurement
│   │   └── alignment.py            # Wire alignment and distortion
│   │
│   ├── classification/
│   │   ├── __init__.py
│   │   └── ml_classifier.py        # Optional ML classification (disabled by default)
│   │
│   ├── output/
│   │   ├── __init__.py
│   │   ├── record.py               # InspectionRecord builder → CSV + JSON
│   │   └── visualiser.py           # Overlay drawing for dashboard display
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── dashboard.py            # Inspection dashboard (technology TBD)
│   │
│   ├── dataset/
│   │   ├── __init__.py
│   │   └── dataset_manager.py      # Sample IDs, manifest, duplicate flagging, split check
│   │
│   ├── hardware/
│   │   ├── __init__.py
│   │   └── esp32_interface.py      # Stub ESP32 serial interface
│   │
│   └── profiles/
│       ├── __init__.py
│       └── profile_manager.py      # Load, validate, select product profiles
│
├── tests/
│   ├── test_profile_manager.py
│   ├── test_calibrator.py
│   ├── test_file_loader.py
│   ├── test_camera.py
│   ├── test_preprocessor.py
│   ├── test_wire_detector.py
│   ├── test_intersection_detector.py
│   ├── test_spacing.py
│   ├── test_alignment.py
│   ├── test_anomaly_detector.py
│   ├── test_ml_classifier.py
│   ├── test_record.py
│   ├── test_visualiser.py
│   ├── test_dataset_manager.py
│   └── test_esp32_interface.py
│
├── outputs/
│   ├── annotated/                  # Annotated output images (never source images)
│   ├── records/                    # CSV and JSON inspection records
│   └── ml_experiments/             # ML training artefacts and metrics (if used)
│
├── dataset_audit/
│   └── DATASET_AUDIT_REPORT.md     # Written after audit, gate for CV implementation
│
├── main.py                         # Pipeline entry point
└── requirements.txt                # Pinned Python dependencies
```

`02_DATASET/` is read-only input. No module in `04_SOFTWARE/` writes to it
under any circumstances.

---

### 2.2 Inspection Pipeline

```
[Image Source]
      │
      ▼
[FR-03] Acquisition
      USB webcam  OR  file loader
      → raw image + timestamp + acquisition mode
      │
      ▼
[FR-04] Preprocessing
      Grayscale → Noise reduction → Contrast enhancement → Perspective correction
      → preprocessed image (working copy; original never modified)
      │
      ▼
[FR-02] Calibration check
      Calibrated? → use px/mm scale factor + spatial confidence
      Uncalibrated? → flag all measurements as UNCALIBRATED; proceed in pixels only
      │
      ▼
[FR-05] Wire Detection
      Algorithm: selected after dataset audit
      → H wire positions (px) + V wire positions (px) + wire widths (px)
      │
      ├──────────────────────────────────────────┐
      ▼                                          ▼
[FR-06] Intersection Detection            [FR-07] Spacing Measurement
      Expected grid vs visible features    Per-gap pixel values
      Detected intersections               Per-gap mm values (if calibrated)
      Missing / abnormal intersections     Mean, std dev
      (visible only — not weld strength)   Nominal reference from profile (ref only)
      │                                          │
      └──────────────────┬───────────────────────┘
                         ▼
      [FR-08] Alignment Analysis + [FR-09] Distortion Analysis
            Per-wire lateral deviation
            Grid skew angle (degrees)
            Spacing variance (H and V)
                         │
                         ▼
            [FR-10] Visual Anomaly Detection
                  Stage 1: Candidate region identification
                        (algorithm: selected after dataset audit)
                  Stage 2: Category assignment
                        (specific category or UNKNOWN if evidence insufficient)
                         │
                         ▼
            [FR-11] ML Classification (conditional — requires audit gate)
                  If enabled and conditions met:
                  → category suggestion + confidence (labelled ML SUGGESTION)
                  If not enabled:
                  → skipped; deterministic result only
                         │
                         ▼
            [FR-12] Location normalisation
                  All anomaly locations → (x, y) pixel coordinates
                  Convert to mm where calibration is valid + spatially applicable
                         │
                         ▼
            [FR-13] Inspection result status
                  PASS / FAIL  — only when validated tolerance exists in profile
                  NOT_CONFIGURED — all current prototype runs (tolerances = null)
                         │
                         ▼
            [FR-14] Inspection Record
                  Assemble InspectionRecord dataclass
                  Save → outputs/records/<inspection_id>.json
                  Save → outputs/records/<inspection_id>.csv
                         │
                         ▼
            [FR-15] Dashboard
                  Annotated image + overlays
                  All measurements + anomalies + ML suggestion
                  Status (NOT_CONFIGURED)
                  Disclaimer always visible
```

---

### 2.3 Data Schemas

#### Product Profile Schema — `config/product_profiles.json`

```json
{
  "profiles": [
    {
      "profile_id": "P001",
      "name": "Kavach / Anti-Climb 358",
      "wire_diameter_h_mm": 4.0,
      "wire_diameter_v_mm": 4.0,
      "aperture_h_mm": 76.2,
      "aperture_v_mm": 12.7,
      "standards": ["BS 1722-14", "EN 10223-7"],
      "corrosion_protection": "Hot-Dip Galvanized + Thermoplastic",
      "tolerances": null
    },
    {
      "profile_id": "P002",
      "name": "Twin Wire Panels",
      "wire_diameter_h_mm": 8.0,
      "wire_diameter_v_mm": 6.0,
      "aperture_h_mm": 200.0,
      "aperture_v_mm": 50.0,
      "standards": ["EN 10223-7", "ISO 9001"],
      "corrosion_protection": "Galvanized + Polyester Powder Coated",
      "tolerances": null
    },
    {
      "profile_id": "P003",
      "name": "UNICO Modular Fence",
      "wire_diameter_options_mm": [4.0, 5.0],
      "aperture_h_mm": 200.0,
      "aperture_v_mm": 50.0,
      "aperture_custom": true,
      "standards": ["EN 10223-7", "DIN 50021"],
      "corrosion_protection": "Polyester Powder Coated (Min 60 μm)",
      "tolerances": null
    }
  ]
}
```

`"tolerances": null` on every profile is intentional.
No tolerance value is populated until formally validated from authoritative
A-1 product documentation. The schema field is reserved so future population
is explicit, auditable, and controlled.

---

#### Pipeline Configuration Schema — `config/pipeline_config.json`

All CV tuning parameters and algorithm selection flags are externalised here.
Specific values are placeholders pending dataset audit. They will be revised
once the dataset has been inspected.

```json
{
  "preprocessing": {
    "noise_reduction_method": "TBD_after_audit",
    "contrast_method": "TBD_after_audit",
    "perspective_correction_enabled": true
  },
  "wire_detection": {
    "algorithm": "TBD_after_audit",
    "parameters": {}
  },
  "intersection_detection": {
    "algorithm": "TBD_after_audit",
    "parameters": {}
  },
  "anomaly_detection": {
    "algorithm": "TBD_after_audit",
    "parameters": {}
  },
  "alignment": {
    "display_deviation_threshold_px": null
  },
  "ml": {
    "enabled": false,
    "feasibility_confirmed": false,
    "model_path": null,
    "min_samples_per_class": null,
    "note": "ML parameters to be determined after dataset audit."
  },
  "output": {
    "save_annotated_images": true,
    "save_csv": true,
    "save_json": true
  }
}
```

Algorithm keys are `"TBD_after_audit"` — this is intentional and marks
unresolved decisions that must be filled in after the dataset audit report
is accepted.

---

#### Inspection Record Schema

```json
{
  "inspection_id": "INS-20260919-001",
  "timestamp": "2026-09-19T21:00:00",
  "acquisition_mode": "file",
  "source_image": "S001_frame_01.jpg",
  "dataset_label": "DEVELOPMENT — Representative sample. Not confirmed A-1 Fence product.",

  "active_profile_id": "P002",
  "active_profile_name": "Twin Wire Panels",

  "calibration": {
    "status": "CALIBRATED",
    "pixels_per_mm": 12.4,
    "reference_target_description": "100mm reference ruler on mesh plane",
    "spatial_confidence_note": "Perspective correction applied. Scale factor valid across corrected image.",
    "uncalibrated_warning": null
  },

  "perspective_correction_applied": true,

  "wire_detection": {
    "algorithm_used": "TBD",
    "horizontal_wires_detected": 8,
    "vertical_wires_detected": 12
  },

  "spacing": {
    "horizontal": {
      "values_px": [],
      "values_mm": [],
      "mean_mm": null,
      "std_dev_mm": null,
      "nominal_ref_mm": 200.0,
      "nominal_ref_label": "Reference only — no validated tolerance"
    },
    "vertical": {
      "values_px": [],
      "values_mm": [],
      "mean_mm": null,
      "std_dev_mm": null,
      "nominal_ref_mm": 50.0,
      "nominal_ref_label": "Reference only — no validated tolerance"
    }
  },

  "alignment": {
    "wires": []
  },

  "distortion": {
    "h_spacing_variance_mm2": null,
    "v_spacing_variance_mm2": null,
    "grid_skew_degrees": null
  },

  "intersections": {
    "expected": null,
    "visually_detected": null,
    "visually_missing_or_abnormal": null,
    "note": "Visible intersection analysis only. Weld strength not assessed."
  },

  "anomalies": [
    {
      "anomaly_id": "A001",
      "category": "SPACING_ANOMALY",
      "defect_status": "REAL",
      "bbox_px": [120, 80, 200, 160],
      "bbox_mm": null,
      "ml_suggestion": null,
      "ml_confidence": null,
      "ml_label": "ML SUGGESTION — not a definitive inspection decision"
    }
  ],

  "inspection_status": "NOT_CONFIGURED",
  "inspection_status_reason": "No validated tolerance exists for this product profile."
}
```

`"inspection_status": "NOT_CONFIGURED"` is the only valid value for all
current prototype runs. The field transitions to PASS or FAIL only when
validated tolerances are added to the active profile.

---

#### Dataset Manifest Schema — `dataset_audit/dataset_manifest.json`

```json
{
  "manifest_version": "1.0",
  "dataset_label": "DEVELOPMENT — Representative sample. Not confirmed A-1 Fence product.",
  "audit_status": "PENDING",
  "samples": [
    {
      "sample_id": "S001",
      "description": "Representative galvanized welded mesh, student-collected",
      "images": [
        {
          "filename": "S001_frame_01.jpg",
          "label": "OK",
          "defect_status": "REAL",
          "near_duplicate_of": null,
          "split_assignment": null,
          "notes": ""
        }
      ]
    }
  ]
}
```

`"split_assignment": null` until the dataset audit confirms a safe split is
possible. `"audit_status": "PENDING"` until the audit report is accepted.

---

### 2.4 Module Responsibility Table

| Module | Inputs | Outputs | Key Constraint |
|---|---|---|---|
| `profile_manager.py` | profiles JSON | ProfileConfig object | No tolerances invented; null is valid |
| `calibrator.py` | reference measurement | scale factor + confidence | Validates calibration before use; flags UNCALIBRATED |
| `file_loader.py` | file path | image array + timestamp | Never modifies source file |
| `camera.py` | device index | image array + timestamp | Mockable for tests |
| `preprocessor.py` | raw image + config | preprocessed working copy | Input array unchanged |
| `wire_detector.py` | preprocessed image + config | H/V wire positions + widths | Algorithm selectable via config |
| `intersection_detector.py` | H wires, V wires, image | expected/detected/missing intersections | Visible features only; no weld strength claim |
| `spacing.py` | wire positions + calibration + profile | gap values, stats, nominal ref | Deviation shown as informational; not PASS/FAIL |
| `alignment.py` | wire positions | per-wire deviation, skew, variance | Display threshold from config |
| `anomaly_detector.py` | preprocessed image + config | candidate regions + categories | Two-stage; UNKNOWN when evidence insufficient; no coating inference |
| `ml_classifier.py` | image crop + model | (category, confidence) or disabled error | Conditional; suggestion only; off by default |
| `record.py` | all pipeline outputs | InspectionRecord → CSV + JSON | status=NOT_CONFIGURED until tolerances validated |
| `visualiser.py` | image + record | annotated image | Never overwrites source |
| `dashboard.py` | record + annotated image | display | Disclaimer always visible; technology TBD |
| `dataset_manager.py` | dataset directory | manifest JSON, split verification | Enforces no cross-sample leakage |
| `esp32_interface.py` | command enum | stub response | No hardware required to import |

---

### 2.5 Hardware Notes

**Current prototype scope:**
- Host laptop running the Python pipeline
- USB webcam (model to be confirmed — OI-02)
- Controlled LED lighting (type to be confirmed — OI-03)
- Physical reference calibration target placed on the mesh plane

**Reference hardware dimensions (from A-1 Launchpad submission):**
The original A-1 Launchpad 2026 submission proposed the following mechanical
configuration. These are design intent values from the competition submission,
not validated final specifications. They are recorded here for reference only.

| Item | Proposed Value | Status |
|---|---|---|
| Base frame | 1800 × 900 × 500 mm | Proposed — not validated |
| Mesh working width | 450 mm | Proposed — not validated |
| Frame material | 40 × 40 mm aluminium profile | Proposed — not validated |
| Rollers | Ø60 × 500 mm | Proposed — not validated |
| Camera-to-mesh distance | 650–700 mm | Proposed — not validated |
| Drive | 12 V DC geared motor, chain and sprocket | Proposed — not validated |
| Power supply | 12 V DC | Proposed — not validated |
| Safety | Fuse + Emergency Stop (E-Stop) | Proposed — hardware detail |
| Motor control | Motor driver + ESP32/Arduino | Proposed — not validated |

The camera-to-mesh distance of 650–700 mm is relevant context for evaluating
whether the selected camera can resolve the finest A-1 mesh aperture
(Kavach: 12.7 mm). This does not replace OI-02 — camera model and optical
resolution remain open until the actual camera is selected and tested.

The fuse and E-Stop are hardware safety components. They do not create
additional software implementation requirements in this prototype.

**ESP32 stub:**
`esp32_interface.py` defines the future command API but all methods return
`{"status": "stub", "message": "ESP32 integration not yet active."}`.
The serial port import is guarded so the module imports successfully on any
machine regardless of hardware availability.

**Future production scope (not in this prototype):**
ESP32 controls a stepper motor, indexes the mesh to successive positions,
triggers capture at each position, and accumulates results into a panel-level
inspection record.

**Future production scope — Coating Defect category:**
The original A-1 Launchpad submission lists "Coating Defect" as a proposed
output category. This is a valid production-scope goal when actual coated
A-1 product samples with reliable labels become available. It is not part
of the current prototype label set. LABELING_RULES.md Rule 6 prohibits
inferring coating defects from the current uncoated representative dataset.
The current anomaly label set retains VISIBLE_SURFACE_ANOMALY as the
conservative substitute. If confirmed coated samples become available in
a future phase, a COATING_ANOMALY category may be added to the label set
at that time, subject to dataset audit.

---

## Part 3 — Implementation Tasks

### Implementation Gate Rules

The following gates must be cleared in order. No phase may begin until its
gate is passed.

| Gate | Condition to proceed |
|------|----------------------|
| Gate 0 | This specification is approved |
| Gate 1 | Dataset audit report (FR-17) is complete and accepted |
| Gate 2 | CV algorithm candidates are selected and agreed from audit findings |
| Gate 3 | ML feasibility decision is documented |
| Gate 4 | Dashboard technology decision is made |

---

### Phase 0 — Foundation (No gates required)

**T-01** Create the `04_SOFTWARE/` directory structure as defined in Section 2.1.
Create all `__init__.py` files. Create empty stub files for every module.

**T-02** Create `requirements.txt` with pinned versions.
Minimum dependencies: `opencv-python`, `numpy`, `pytest`.
Optional (pending audit): `scikit-learn`, `Pillow`.
Verify the environment installs cleanly on the development machine.

**T-03** Create `config/product_profiles.json` with the three A-1 product
profiles exactly as specified in Section 2.3. All `"tolerances": null`.

**T-04** Create `config/pipeline_config.json` with the schema from Section 2.3.
All algorithm keys set to `"TBD_after_audit"`. This file documents known-open
decisions explicitly.

**T-05** Implement `src/profiles/profile_manager.py`:
- Load and validate profiles from JSON
- Expose `get_profile(profile_id)` returning a typed ProfileConfig object
- Raise a descriptive error for unknown profile IDs
- Unit test: load all three profiles; assert `tolerances` is null for all;
  assert unknown ID raises error; assert UNICO custom flag is present.

---

### Phase 1 — Dataset Audit (Gate 0 required; produces Gate 1)

**T-06** Unzip `02_DATASET/a1zip.zip` into a read-only working directory
(do not unzip into the source dataset directory structure in a way that
mixes processed and original files).

**T-07** Implement `src/dataset/dataset_manager.py`:
- Scan the dataset directory and assign sample IDs to image groups
- Write a dataset manifest following the schema in Section 2.3
- Provide `verify_split(train_list, test_list)` — raises error on overlap
- Provide `flag_near_duplicates(image_list)` — perceptual hash comparison
- Manifest always includes the disclaimer label
- Unit test: mock directory with known image groupings → correct manifest;
  split with overlapping sample → error raised; near-duplicate pair → flagged.

**T-08** Conduct the dataset audit using the dataset_manager output.
Write `dataset_audit/DATASET_AUDIT_REPORT.md` covering all items in FR-17:
total images, physical sample count, label distribution, defect status
distribution, near-duplicates, leakage risk, ML feasibility decision,
CV algorithm candidates, and any required labelling corrections.

**T-09** Review and accept the audit report.
Fill in `config/pipeline_config.json` algorithm keys with the agreed
algorithm choices. Update `pipeline_config.json` with audit-derived
parameter starting points (replacing all `"TBD_after_audit"` entries).
This marks Gate 1 and Gate 2 as cleared.

---

### Phase 2 — Acquisition and Calibration (Gate 1 required)

**T-10** Implement `src/acquisition/file_loader.py`:
- Load an image from a file path using OpenCV
- Return the image array and a timestamp
- Unit test: load a test image; assert shape is valid; assert source file
  is byte-for-byte identical after load (no modification).

**T-11** Implement `src/acquisition/camera.py`:
- Wrap `cv2.VideoCapture` for USB webcam
- Expose `capture_frame()` returning image array + timestamp
- Unit test: mock `VideoCapture`; assert return types.

**T-12** Implement `src/calibration/calibrator.py`:
- Accept a known reference length in mm and the corresponding pixel measurement
  from a target placed on the mesh plane
- Compute and store the px/mm scale factor
- Validate that the scale factor is physically plausible (configurable
  plausibility bounds)
- Expose `to_mm(pixels)`, `is_calibrated()`, `confidence_note()`
- If perspective distortion is not fully corrected, record a spatial
  confidence note in the calibration result
- If not calibrated, `to_mm()` raises a CalibratorNotReadyError rather than
  silently returning a value
- Unit test: known input → known scale factor; out-of-bounds scale factor →
  validation error; uncalibrated call → CalibratorNotReadyError.

---

### Phase 3 — Preprocessing (Gate 1 required)

**T-13** Implement `src/preprocessing/preprocessor.py`:
- Accept a raw image and the pipeline config
- Apply: grayscale conversion, noise reduction (method from config),
  contrast enhancement (method from config), perspective correction
  (transform from supplied reference points, or identity with flag if none)
- Return preprocessed working copy
- Assert input array is not modified
- Unit test: synthetic image → output is grayscale; perspective correction
  with known points → output matches expected transform; no-correction case →
  flag is set in returned metadata.

---

### Phase 4 — Wire and Intersection Detection (Gates 1 and 2 required)

**T-14** Implement `src/detection/wire_detector.py`:
- Accept preprocessed image and pipeline config
- Use the algorithm specified in `pipeline_config.json["wire_detection"]["algorithm"]`
- Return: H wire y-positions (px), V wire x-positions (px), estimated wire
  widths (px) per wire
- The algorithm is encapsulated. The interface (inputs and outputs) does not
  change if the algorithm is switched.
- Unit test: synthetic image with a known wire grid → detected count matches;
  changing the algorithm key in config routes to the correct implementation.

**T-15** Implement `src/detection/intersection_detector.py`:
- Accept H wire positions, V wire positions, and preprocessed image
- Compute all expected grid intersections
- For each expected intersection, check whether a visible feature is present
  at that location using the method from config
- Return: expected intersections list, detected intersections list,
  missing/abnormal intersections list
- Record the intersection note: "Visible intersection analysis only.
  Weld strength not assessed."
- Unit test: synthetic grid with one removed intersection → missing count == 1.

---

### Phase 5 — Measurement (Gate 1 required)

**T-16** Implement `src/measurement/spacing.py`:
- Accept H wire positions, V wire positions, calibration object, and
  active profile
- Compute all inter-wire gaps (H and V)
- Return: pixel values, mm values (only if `calibrator.is_calibrated()` is
  True and calibration is spatially applicable), mean, std dev, and nominal
  reference from profile (clearly labelled as reference only)
- Unit test: known positions → known gaps; uncalibrated → mm fields are null;
  UNICO with custom aperture and no runtime value → nominal_ref is null.

**T-17** Implement `src/measurement/alignment.py`:
- Accept H wire positions and V wire positions
- For each wire, fit a straight reference line and compute maximum lateral
  deviation
- Compute grid skew angle (degrees from horizontal/vertical)
- Compute spacing variance (H and V separately)
- Unit test: perfectly regular synthetic grid → deviation ≈ 0, skew ≈ 0,
  variance ≈ 0.

---

### Phase 6 — Anomaly Detection (Gates 1 and 2 required)

**T-18** Implement `src/detection/anomaly_detector.py`:
- Accept preprocessed image, pipeline config, and detected wire grid
- Stage 1: identify candidate anomaly regions using the algorithm specified
  in config. Return candidate bounding boxes.
- Stage 2: for each candidate, assign a category from the allowed label set
  or UNKNOWN if evidence is insufficient
- Never assign a category by assumption
- Never infer coating defects from uncoated mesh images
- The algorithm is encapsulated; the interface is stable
- Unit test: regular synthetic mesh → no anomalies; mesh with a removed wire
  segment → at least one anomaly candidate; mesh with ambiguous region →
  UNKNOWN category.

---

### Phase 7 — Output and Visualisation (Gate 1 required)

**T-19** Implement `src/output/record.py`:
- Define an `InspectionRecord` dataclass with all fields from Section 2.3
- Implement `save_csv(record, path)` and `save_json(record, path)`
- `inspection_status` must be NOT_CONFIGURED unless a validated tolerance
  is present in the profile
- `dataset_label` must always contain the full disclaimer string
- `intersections.note` must always contain the weld-strength disclaimer
- Unit test: build a minimal record, save to temp directory, reload and
  verify: inspection_status == NOT_CONFIGURED; dataset_label is correct;
  intersection note is present; pass_fail key does not exist.

**T-20** Implement `src/output/visualiser.py`:
- Accept a raw or preprocessed image and an InspectionRecord
- Draw overlays: detected wires, intersections (present), missing/abnormal
  intersections (distinctly marked), anomaly bounding boxes with category labels
- Save annotated image to `outputs/annotated/<inspection_id>_annotated.jpg`
- Return annotated image array
- Never overwrite any file in `02_DATASET/`
- Unit test: blank input image + minimal record → output differs from input
  (overlays drawn); source dataset path not touched.

---

### Phase 8 — Pipeline Integration (All previous phases required)

**T-21** Implement `main.py`:
- Accept CLI arguments: `--source` (file path or `webcam`),
  `--profile` (profile ID), `--calibration` (optional px/mm value)
- Wire the full pipeline in the order defined in Section 2.2
- If no calibration is supplied, print a clear UNCALIBRATED warning and
  proceed with pixel-only measurements
- Print a one-line inspection summary to stdout
- Save inspection record and annotated image to `outputs/`

**T-22** Implement `src/hardware/esp32_interface.py` stub:
- Define `connect(port)`, `move_to_position(index)`, `home()`,
  `get_status()`, `disconnect()`
- All return `{"status": "stub", "message": "ESP32 integration not active."}`
- Serial library import guarded: `try: import serial except ImportError: serial = None`
- Unit test: instantiate without hardware; all methods return stub status dict.

---

### Phase 9 — ML Classification (Gates 1 and 3 required)

**T-23** Implement `src/classification/ml_classifier.py`:
- Gate check: `ml.enabled` must be True and `ml.feasibility_confirmed` must
  be True in pipeline config before any ML code runs
- If gate check fails, `classify()` raises `MLNotEnabledError` with a clear message
- If enabled: load model from `ml.model_path`; expose `classify(image_crop)`
  returning `(category, confidence)` — always labelled as ML SUGGESTION
- Provide `train(manifest_path, output_path)` with explicit split leakage check
  before training begins
- Record and save precision, recall, F1 per class to `outputs/ml_experiments/`
- Unit test: disabled config → MLNotEnabledError; mock-enabled with mock model
  → returns correct tuple type; leaky split → train raises error.

---

### Phase 10 — Dashboard (Gates 1 and 4 required)

**T-24** Implement `src/dashboard/dashboard.py`:
- Display all content items listed in FR-15
- The disclaimer string must be visible on every frame
- The inspection status (NOT_CONFIGURED) must be displayed
- Technology: as agreed at Gate 4 (OpenCV window, Tkinter, or other)
- Unit test: render with a minimal InspectionRecord and verify no exception;
  verify disclaimer string is present in rendered output.

---

### Phase 11 — Verification

**T-25** End-to-end integration test:
- Run `main.py` with at least one image from the dataset, a selected profile,
  and a manual calibration value
- Verify: inspection record JSON saved; `inspection_status == "NOT_CONFIGURED"`;
  `dataset_label` contains disclaimer; `intersections.note` contains weld disclaimer;
  source dataset image is byte-for-byte unchanged (compare checksums before and after)

**T-26** Run all unit tests: `pytest tests/ -v`.
All tests must pass before any demonstration or submission build.

**T-27** Measure and record actual pipeline processing time on the development
laptop for a 1920×1080 image. Compare against the 10-second prototype target
(NFR-06). If the target is not met, document the bottleneck. Do not optimise
prematurely — measure first.

**T-28** Evaluate prototype performance using the metrics from the original
A-1 Launchpad submission. These metrics have not yet been measured; this
task records the requirement to measure them during verification.

For the anomaly detection and ML classification outputs (where applicable),
compute and record:
- Accuracy (overall correct classifications / total samples)
- Precision (per class: true positives / (true positives + false positives))
- Recall (per class: true positives / (true positives + false negatives))
- False-reject rate (OK samples incorrectly flagged as defective / total OK samples)
- Repeatability under fixed lighting: run the same image through the pipeline
  N times under identical lighting conditions and record whether the output
  is identical on every run (deterministic check, per NFR-07)

These metrics are to be measured, not assumed. Results are to be saved to
`outputs/ml_experiments/` or `outputs/records/` as appropriate.
No performance claim is made in this specification.

---

## Open Items

These remain unresolved. They do not block the spec, but they block specific
implementation phases as noted.

| ID    | Issue | Blocks |
|-------|-------|--------|
| OI-01 | ~~`A1 Titans_A-1 Launchpad.pdf` content could not be extracted.~~ **RESOLVED.** PDF extracted and compared against all markdown master documents. Findings: (1) camera-to-mesh distance 650–700 mm added to hardware notes; (2) validation metrics (accuracy, precision, recall, false-reject rate, repeatability) added as T-28; (3) Coating Defect category recorded as future production scope in hardware notes; (4) fuse, E-Stop, 12 V supply, motor driver recorded as hardware reference details. No conflicts found that require changes to requirements FR-01 through FR-18. No new functional requirements identified. | Resolved — no longer blocks spec approval. |
| OI-02 | Camera model and intended working distance from mesh to lens are unconfirmed. The PDF proposes 650–700 mm as the camera-to-mesh distance (hardware reference only — not validated). Camera optical resolution and whether it can resolve the Kavach 12.7 mm aperture at that distance remain unconfirmed. | Camera model and optical specification required. Blocks: T-11, T-12. |
| OI-03 | Lighting type (ring / raking / diffuse) is unconfirmed. Specular reflections from galvanized wire can break edge-based detection. | Lighting decision required. Blocks: T-14 (algorithm choice depends on illumination type). |
| OI-04 | Dataset has not been audited. Image count, label distribution, format, quality, and sample groupings are unknown. | Blocks: Gate 1. Nothing in Phase 4 onwards may proceed. |
| OI-05 | No sample ID scheme exists in the dataset yet. Data leakage risk is unquantified. | Blocks: T-08, any train/test split. |
| OI-06 | Dashboard technology is undefined. | Blocks: Gate 4. Blocks: T-24. |
| OI-07 | UNICO profile has a custom aperture option with no defined runtime entry mechanism. | Blocks: T-16 (spacing for UNICO custom). |

---

*End of Specification — Revision 3*
*No implementation code shall be written until this document has been reviewed,
open items addressed, and explicit approval given.*
