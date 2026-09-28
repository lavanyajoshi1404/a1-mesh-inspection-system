# Project Scope and Limitations

## Prototype Scope

The prototype demonstrates:

- Camera-based welded mesh inspection
- Mesh geometry detection
- Mesh spacing measurement
- Wire alignment analysis
- Weld/intersection analysis
- Visual anomaly detection
- Optional ML-based anomaly classification
- Inspection result visualization
- Digital inspection records
- Configurable product profiles
- Future ESP32-controlled indexed inspection

## Current Dataset Limitation

Physical A-1 product samples are currently unavailable.

Therefore representative welded-wire-mesh samples are used for
algorithm development.

## Current Product Limitation

The prototype should not claim that the current dataset represents
A-1 production material.

## Material Property Limitations

Computer vision alone does not directly measure:

- tensile strength
- weld strength
- coating adhesion
- coating thickness
- corrosion resistance
- salt-spray performance

## Production Deployment Requirements

A production deployment would require:

- actual A-1 product samples
- validated product specifications
- validated acceptance tolerances
- camera calibration
- controlled illumination
- larger representative datasets
- production-line testing
- appropriate physical quality testing
- industrial hardware validation