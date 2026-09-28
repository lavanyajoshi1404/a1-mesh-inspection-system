# Dataset Labeling Rules

## Primary Categories

OK
SPACING_ANOMALY
WELD_INTERSECTION_ANOMALY
ALIGNMENT_DISTORTION
VISIBLE_SURFACE_ANOMALY
UNKNOWN

## Defect Status

REAL
SIMULATED
UNKNOWN

## Rules

1. Do not call an image defective unless there is evidence.
2. Do not create a defect by editing an image and then label it REAL.
3. Simulated defects must remain SIMULATED.
4. Unknown images remain UNKNOWN.
5. Do not infer that a sample belongs to A-1.
6. Do not infer coating defects from an uncoated mesh.
7. If the defect cannot be confidently identified, use UNKNOWN.