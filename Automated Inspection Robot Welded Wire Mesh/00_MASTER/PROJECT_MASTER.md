# A1 Mesh Inspection — Project Master

## Project

Automated Quality Inspection System for Welded Wire Mesh

## Team

A1 Titans

## Objective

Develop a portable, low-cost computer-vision-based prototype for
automated visual inspection of welded wire mesh.

The prototype should demonstrate how camera-based inspection can
analyze mesh geometry and visible anomalies and provide digital
inspection results.

The architecture should be capable of future integration into an
A-1 Fence production environment.

---

## Current Situation

Physical A-1 product samples are currently unavailable.

Representative welded-wire-mesh samples are available and will be
used for initial computer-vision development.

The representative samples must NOT be described as confirmed
A-1 Fence products.

The current dataset is therefore a development dataset.

---

## A-1 Alignment

The software architecture must be aligned with the documented
A-1 Fence welded-mesh product specifications.

The initial product reference profiles are:

1. A-1 Kavach / Anti-Climb 358
2. A-1 Twin Wire Panels
3. A1 UNICO Modular Fence

Product specifications must be stored as configurable product profiles.

The system must not hard-code one mesh geometry.

---

## Core Inspection Parameters

The prototype should investigate:

1. Mesh aperture / spacing
2. Horizontal wire alignment
3. Vertical wire alignment
4. Wire intersections / weld locations
5. Missing or abnormal intersections where visually detectable
6. Mesh distortion
7. Visible visual anomalies
8. Defect location
9. Inspection traceability

---

## System Does NOT Claim

The camera system does not directly measure:

- tensile strength
- weld shear strength
- coating thickness
- coating adhesion
- salt-spray resistance
- structural strength

These require appropriate physical/material testing methods.

---

## Hardware

- Laptop
- USB webcam
- Controlled LED lighting
- Welded wire mesh sample
- ESP32
- Motor/driver where applicable
- Portable mechanical structure

---

## Software

- Python
- OpenCV
- Machine learning where justified
- Dashboard
- CSV/JSON inspection records
- ESP32 serial communication

---

## Computer-Vision Inspection Pipeline

Image
↓
Preprocessing
↓
Wire/Grid Detection
↓
Intersection Detection
↓
Intersection Analysis
↓
Mesh Spacing Measurement
↓
Inspection Decision
↓
Dashboard / Report

## Proposed System Architecture

Welded Wire Mesh
↓
Mesh Transport / Positioning
↓
Inspection Position
↓
Camera + Illumination
↓
Image Acquisition
↓
Computer Vision
↓
Wire/Grid Detection
↓
Intersection Analysis
↓
Spacing Measurement
↓
Inspection Decision
↓
Dashboard
↓
Inspection Record

---

## Engineering Principles

1. Use deterministic computer vision for measurable geometry.
2. Use ML only where it provides meaningful additional value.
3. Never invent dataset labels.
4. Never represent representative mesh as confirmed A-1 mesh.
5. Keep product specifications configurable.
6. Never invent A-1 tolerances.
7. Never claim visual inspection measures material properties that it
   cannot actually measure.
8. Preserve original dataset images.
9. Avoid data leakage between training and testing.
10. Every major module must be testable.