# Welded Mesh Development Dataset

## Purpose

This dataset is used to develop and test the computer-vision pipeline
for the A1 Mesh Inspection project.

## Important

These are representative welded-wire-mesh samples.

They are not confirmed A-1 Fence products.

## Dataset Uses

The dataset may be used for:

- mesh detection
- wire detection
- spacing analysis
- alignment analysis
- intersection detection
- visual anomaly analysis
- ML experimentation where sufficient labels exist

## Dataset Rules

1. Original images must not be modified.
2. Processed images must be stored separately.
3. Every physical mesh sample should have a unique sample ID.
4. Near-duplicate images should be identified.
5. Images from the same physical sample should not be split across
   train and test in a way that causes data leakage.
6. Unknown labels must remain UNKNOWN.
7. Simulated defects must be explicitly identified.
8. Real defects must be explicitly identified.