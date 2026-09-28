"""
Central configuration for the A1 Mesh Inspection software.

This module intentionally contains ONLY what Milestone 1 needs: where to
find/write images locally, and which file formats we accept. Do NOT add
camera settings, calibration values, PASS/FAIL tolerances, or dashboard
config here until those modules are actually being implemented - an
unused config value is a placeholder in disguise.
"""

from pathlib import Path

# 04_SOFTWARE/ is the parent of this config/ package.
SOFTWARE_ROOT = Path(__file__).resolve().parent.parent

# Where known-good input images for manual testing/dev live.
DATA_INPUT_DIR = SOFTWARE_ROOT / "data" / "input"

# Where this milestone writes its verification output (e.g. a saved
# copy confirming a successful read). This is the ONLY place this
# milestone ever writes to - the original 02_DATASET is never touched.
DATA_PROCESSED_DIR = SOFTWARE_ROOT / "data" / "processed"

# The audited dataset (see 02_DATASET/AUDIT) is JPEG only, so this is
# intentionally narrow rather than "accept any image cv2 can decode".
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg"}


# --- Milestone 2: preprocessing ---
# Every value below is tied to a measurement taken on a real dataset
# image (IMG_20260920_200712.jpg, 3000x4000), not a guessed default.
# See core/preprocessing.py for how each is used.

# Wire thickness measured via an Otsu-threshold scanline at full
# resolution was ~38-51 px. Downscaling so the long side is 1600 px
# still leaves ~15-20 px of wire thickness - comfortably enough for
# later edge/line work - while cutting processing cost on a 12MP
# source. This only ever downscales (never upscales); set to None to
# disable resizing entirely.
PREPROCESS_MAX_DIMENSION = 1600

# Corner-to-corner brightness on the sample image varied by ~75 units
# (measured), confirming real, spatially uneven illumination - CLAHE
# (local/adaptive) is used rather than global equalization for that
# reason. Clip limit kept modest since we're correcting shadow, not
# manufacturing detail that isn't there.
PREPROCESS_CLAHE_CLIP_LIMIT = 2.0
PREPROCESS_CLAHE_TILE_GRID = (16, 16)

# Measured local background noise (std) was ~4.2 in flat regions - low.
# These bilateral filter parameters are deliberately mild: enough to
# knock down rust-texture micro-noise ahead of edge detection without
# acting like a heavy denoiser the measured noise level doesn't justify.
PREPROCESS_BILATERAL_DIAMETER = 5
PREPROCESS_BILATERAL_SIGMA_COLOR = 50
PREPROCESS_BILATERAL_SIGMA_SPACE = 50

# --- Milestone 3: calibration ---
# Calibration works on the FULL-RESOLUTION original image, not the
# Milestone 2 preprocessed/downscaled output - tick marks a few px wide
# need full resolution to be measured reliably. This keeps calibration
# independent of the mesh-detection preprocessing pipeline.

# A tick-spacing sample is kept only if it falls within this fraction of
# the median spacing (e.g. 0.3 = accept 70%-130% of the median). Wider
# deviations are treated as a missed or double-counted tick, not real
# spacing variation. Value chosen empirically: on the real test image
# this correctly rejected 2 of 40 spacings (edge/detection artifacts)
# while keeping the other 38 at <4% relative spread - tightening much
# further started rejecting genuine ticks.
CALIBRATION_OUTLIER_TOLERANCE = 0.3

# A calibration attempt is only marked validated if at least this
# fraction of detected spacings are inliers (see above) AND the inlier
# spacings' std/mean ratio is at or below CALIBRATION_MAX_CV. On the
# real test image the achieved values were 38/40 = 95% inliers and a
# 4% ratio - both comfortably inside these thresholds, which is why
# they're set here rather than loosened to force a pass.
CALIBRATION_MIN_INLIER_FRACTION = 0.8
CALIBRATION_MAX_CV = 0.10

# Minimum pixel gap enforced between two accepted tick peaks, and the
# minimum brightness drop (prominence) a candidate peak must show
# against its local surroundings to count as a tick rather than noise.
# Chosen from the measured mm-tick spacing (~20 px) on the real image -
# distance is set below that so real ticks aren't merged, prominence
# was tuned to admit genuine ticks while rejecting faint JPEG noise.
CALIBRATION_MIN_TICK_DISTANCE_PX = 8
CALIBRATION_MIN_TICK_PROMINENCE = 15

# Standard metric ruler assumption: minor ticks are 1 mm apart. This is
# a documented property of the ruler design visible in the source
# photos (Faber-Castell student ruler, confirmed by manually counting
# 10 subdivisions between consecutive cm marks) - not a measured or
# invented value, and it is configurable if a different ruler is used.
CALIBRATION_MM_PER_TICK = 1.0

# Detects a systematic drift in tick spacing across the ROI (e.g. from
# perspective/tilt) that the outlier/CV check above can miss, because a
# smooth drift never looks like a local outlier - each spacing is close
# to its neighbors, it's the trend across many ticks that's the problem.
# Measured via the Pearson correlation between tick index and spacing;
# a real test image showed a spacing sequence climbing smoothly from 27
# to 34 px (a ~25% systematic change) with correlation ~0.97 - so this
# threshold is set well below that, at a point where a real drift is
# still clearly separable from random scatter.
CALIBRATION_MAX_DRIFT_CORRELATION = 0.5

# --- Milestone 4: wire/grid detection ---
# Every value below is tied to a measurement taken on the real
# preprocessed edge output (preprocessed_IMG_20260920_200712_edges.jpg,
# 1200x1600), not a guessed default. See core/wire_detection.py.

# cv2.HoughLinesP parameters. threshold=80 and min_line_length=200
# (~1/6 of the 1200px-wide test image) were the values that produced a
# clean detection on the real edge map: 85 line segments total, with
# angles cleanly separated into two tight clusters (near 0 deg and near
# 90 deg) and no significant population in between - i.e. this already
# discriminates real wire edges from noise without further filtering.
WIRE_HOUGH_RHO = 1
WIRE_HOUGH_THETA_DEG = 1
WIRE_HOUGH_THRESHOLD = 80
WIRE_HOUGH_MIN_LINE_LENGTH_PX = 200
WIRE_HOUGH_MAX_LINE_GAP_PX = 20

# A detected line segment is classified as horizontal/vertical only if
# its angle is within this many degrees of 0/180 (horizontal) or 90
# (vertical). Measured angle histogram on the real image showed two
# tight clusters (around -5 to 0 deg, and around 85 deg) with a large
# empty gap to anything else - 15 deg comfortably contains the real
# clusters without being anywhere near diagonal noise.
WIRE_ANGLE_TOLERANCE_DEG = 15

# Two detected line segments are merged into the same physical wire if
# their positions (y for horizontal, x for vertical) are within this
# many pixels of each other. Measured on the real image: gaps between
# segments belonging to the SAME wire (its two edges, or fragments from
# a slightly bowed wire) were all <=19px; gaps between DIFFERENT wires
# were all >=205px. 40px sits with a wide safety margin inside that gap.
WIRE_CLUSTER_DISTANCE_PX = 40

# When checking whether a horizontal and vertical wire actually cross
# within the image (not just extrapolate to a hypothetical crossing
# point), each wire's own detected pixel extent is allowed to fall
# short of the other wire's position by up to this many pixels - real
# wire endpoints are jagged/rounded in the edge map, not exact.
WIRE_INTERSECTION_TOLERANCE_PX = 15

# --- Milestone 5: intersection/weld-region appearance ---
# Values justified on the real image (IMG_20260920_200712, 1200x1600
# preprocessed scale). See core/weld_intersection.py.

# Local ROI half-size around each intersection for appearance analysis.
# Measured minimum wire spacing on the real image was ~253px between
# adjacent wires; 60px leaves each ROI well clear of the neighboring
# intersection (roughly half the minimum spacing, with margin).
WELD_ROI_HALF_SIZE_PX = 60

# For checking whether a wire "arm" extends from an intersection in a
# given direction: skip this many pixels nearest the intersection
# center (avoids the crossing's own bulk/blur) before starting the
# measurement band, and stop this many pixels out (keeps the band
# inside the ROI).
WELD_ARM_INNER_MARGIN_PX = 15
WELD_ARM_OUTER_RADIUS_PX = 55

# Half-width of the measurement band perpendicular to each arm's
# direction. Matches the measured wire thickness at this image scale
# (~15-20px) with a small margin either side, so the band reliably
# covers the wire even with a few pixels of position error.
WELD_ARM_BAND_HALF_WIDTH_PX = 10

# An arm direction is classified "present" (dark/wire-colored) if its
# band's mean grayscale intensity is below the image's own Otsu
# threshold (recomputed per-image, the same data-derived method
# Milestone 2 uses - not a fixed number). Validated against 12 real,
# manually-confirmed arm observations (4 arms x 3 intersections of
# known grid position: one full interior 4-way, one top-row 3-way, one
# top-left corner 2-way) - this rule matched all 12/12 by hand.

# --- Milestone 6: mesh spacing measurement ---
# This is a fixed, manually-set vertical scale estimate. It is NOT the output
# of a passed core.calibration.calibrate_from_ruler() validation run: the one
# real ruler-image run on record for this project (see
# data/results/calibration_IMG_20260920_201817_vertical.json) returned
# NOT_VALIDATED (drift check failed), and core.calibration is not currently
# invoked by this pipeline. Its status is therefore UNVALIDATED ESTIMATE, not
# PROVISIONAL - "PROVISIONAL" in this codebase specifically means a
# core.calibration run that passed its own statistical validation
# (VALIDATED_SINGLE_AXIS_PROVISIONAL), which this value does not represent.
CALIBRATION_VERTICAL_PX_PER_MM = 11.0
CALIBRATION_VERTICAL_STATUS = "UNVALIDATED ESTIMATE"

# Horizontal axis has documented position-dependent variation (perspective/tilt)
# and no confirmed horizontal scale. Preserved as uncalibrated rather than
# inventing an unsupported single global horizontal scale.
CALIBRATION_HORIZONTAL_PX_PER_MM = None
CALIBRATION_HORIZONTAL_STATUS = "UNCALIBRATED"

# M-3: shared caveat text for exported evidence that pairs a measured spacing
# with a reference product profile's nominal spacing. The current development
# samples are not confirmed A-1 production material, so a numeric difference
# between the two must never be read as a product-spec deviation or defect.
SAMPLE_VS_PROFILE_CAVEAT = (
    "The measured spacing values come from the current representative "
    "development sample. The referenced product profile is a reference/"
    "nominal specification only - this sample has NOT been confirmed as "
    "A-1 material matching this profile. Any numeric difference between "
    "measured and nominal values must NOT be interpreted as a product-spec "
    "deviation or a defect result."
)

# M-5: single shared source for the vertical-scale calibration caveat, used
# both by core.inspection_decision (REVIEW reasons) and
# dashboard.utils.pipeline_runner (Calibration Caveat evidence item), so the
# wording cannot drift out of sync between the two call sites.
CALIBRATION_CAVEAT_UNVALIDATED_ESTIMATE = (
    "Vertical spacing scale is an UNVALIDATED ESTIMATE (fixed single-axis "
    "reference value; not derived from a passed core.calibration validation "
    "run; plane offset and lens distortion not corrected)."
)
CALIBRATION_CAVEAT_PROVISIONAL = (
    "Vertical spacing calibration is PROVISIONAL (single-axis ruler "
    "calibration; plane offset and lens distortion not corrected)."
)
