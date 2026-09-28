"""
Milestone 3 - calibration.

Computes a pixel-to-mm scale factor from a ruler visible in a photo, by
detecting the ruler's periodic tick marks and measuring their spacing.

This module makes NO PASS/FAIL, geometry, or defect decision. It only
answers one narrow question: "does this image support a statistically
validated pixel-to-mm scale along one axis, and if so, what is it?" -
and it refuses to answer (raises / returns not-validated) rather than
guess when the evidence doesn't support it.

Scope and honesty notes (see project audit for full detail):
  - This computes a SINGLE-AXIS, PROVISIONAL calibration from ONE image.
    It is not a general, multi-image, 2D, lens-distortion-corrected
    calibration - that is future work if this becomes a recurring
    procedure rather than a one-off measurement.
  - The tick-mark ROI (which columns/rows actually contain clean tick
    marks, free of text/logos/mesh) is NOT auto-detected - it must be
    supplied by the caller. Auto-locating a ruler reliably in an
    arbitrary photo is a materially harder problem than measuring tick
    spacing once the band is known, and guessing it here would risk
    silently calibrating against the wrong stripe (e.g. printed text).
  - The ruler lies flat on the background; the wire mesh has real
    height above that plane. This introduces a small, unquantified
    parallax error for a non-orthographic camera. Not corrected here.
  - The resulting px-per-mm value is specific to the camera distance/
    zoom used for THIS photo. It is not valid for other images unless
    capture distance is held fixed.

Operates on the FULL-RESOLUTION original image (via core.image_loader),
not the Milestone 2 preprocessed/downscaled output - tick marks a few
pixels wide need full resolution to be measured reliably. This keeps
calibration independent of the mesh-detection preprocessing pipeline.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Literal, Optional, Tuple

import cv2
import numpy as np

from config.settings import (
    CALIBRATION_MAX_CV,
    CALIBRATION_MAX_DRIFT_CORRELATION,
    CALIBRATION_MIN_INLIER_FRACTION,
    CALIBRATION_MIN_TICK_DISTANCE_PX,
    CALIBRATION_MIN_TICK_PROMINENCE,
    CALIBRATION_MM_PER_TICK,
    CALIBRATION_OUTLIER_TOLERANCE,
)

Axis = Literal["vertical", "horizontal"]


class CalibrationError(Exception):
    """Raised when a calibration attempt cannot be performed at all
    (bad input), as distinct from being attempted but not validated."""


@dataclass
class CalibrationResult:
    """Structured, factual record of a calibration attempt.

    status is one of:
      "VALIDATED_SINGLE_AXIS_PROVISIONAL" - tick spacing passed the
          consistency checks; px_per_mm is usable with the caveats
          documented above and repeated in `notes`.
      "NOT_VALIDATED" - tick detection ran but did not pass the
          consistency checks; px_per_mm is None. See diagnostics.

    This never reports a plain "CALIBRATED" status - deliberately, so
    downstream code cannot mistake this for a full, production-grade,
    2D, distortion-corrected calibration.
    """
    source_name: str
    axis: Axis
    roi: Tuple[int, int, int, int]     # (x_start, x_end, y_start, y_end)
    status: str
    px_per_mm: Optional[float]
    mm_per_tick_assumed: float
    ticks_detected: int
    spacings_px: List[int]
    inlier_count: int
    inlier_fraction: float
    inlier_cv: Optional[float]         # coefficient of variation (std/mean) of inlier spacings
    drift_correlation: Optional[float]  # correlation of spacing vs. tick order; large |value| = systematic drift, not noise
    notes: str


def _find_peaks(signal: np.ndarray, min_distance: int, min_prominence: float) -> np.ndarray:
    """Minimal local-maxima peak finder (no scipy dependency needed for
    this one use). Finds local maxima, keeps those whose value exceeds
    the local minimum within +/- min_distance by at least
    min_prominence, then greedily non-max-suppresses by min_distance.
    """
    n = len(signal)
    candidates = [i for i in range(1, n - 1) if signal[i] >= signal[i - 1] and signal[i] >= signal[i + 1]]

    scored = []
    for i in candidates:
        lo = max(0, i - min_distance)
        hi = min(n, i + min_distance + 1)
        baseline = signal[lo:hi].min()
        prominence = signal[i] - baseline
        if prominence >= min_prominence:
            scored.append((signal[i], i))

    scored.sort(reverse=True)
    accepted: List[int] = []
    for _, i in scored:
        if all(abs(i - j) >= min_distance for j in accepted):
            accepted.append(i)

    return np.array(sorted(accepted))


def calibrate_from_ruler(
    image: np.ndarray,
    source_name: str,
    roi: Tuple[int, int, int, int],
    axis: Axis = "vertical",
    mm_per_tick: float = CALIBRATION_MM_PER_TICK,
) -> CalibrationResult:
    """Attempt a single-axis pixel-to-mm calibration from a ruler ROI.

    Args:
        image: Full-resolution image array (BGR, as read by OpenCV).
        source_name: Name for reporting (e.g. the source filename).
        roi: (x_start, x_end, y_start, y_end) pixel bounds of a strip
            containing ONLY the ruler's tick marks - no numerals, logos,
            or mesh. Must be identified by the caller (see module
            docstring for why this isn't auto-detected).
        axis: "vertical" if the ruler's ticks run top-to-bottom in the
            image, "horizontal" if they run left-to-right.
        mm_per_tick: Real-world spacing of the ruler's minor ticks.
            Defaults to the standard metric assumption (1 mm), see
            config/settings.py for how that was confirmed on the real
            reference photo.

    Returns:
        A CalibrationResult. Check `.status` before trusting `.px_per_mm`
        - it is None whenever status is "NOT_VALIDATED".

    Raises:
        CalibrationError: for invalid input (bad image/ROI), not for a
            failed calibration attempt (that's a NOT_VALIDATED result).
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise CalibrationError("calibrate_from_ruler received an empty or invalid image array.")

    x0, x1, y0, y1 = roi
    height, width = image.shape[:2]
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise CalibrationError(f"ROI {roi} is out of bounds for image of size {width}x{height}.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    band = gray[y0:y1, x0:x1]

    # Average across the band's short dimension to get a 1D profile
    # along the ruler's long axis, then invert so dark ticks are peaks.
    if axis == "vertical":
        profile = band.mean(axis=1).astype(np.float64)
    elif axis == "horizontal":
        profile = band.mean(axis=0).astype(np.float64)
    else:
        raise CalibrationError(f"axis must be 'vertical' or 'horizontal', got {axis!r}")

    inverted = profile.max() - profile

    peaks = _find_peaks(
        inverted,
        min_distance=CALIBRATION_MIN_TICK_DISTANCE_PX,
        min_prominence=CALIBRATION_MIN_TICK_PROMINENCE,
    )

    if len(peaks) < 3:
        return CalibrationResult(
            source_name=source_name, axis=axis, roi=roi,
            status="NOT_VALIDATED", px_per_mm=None,
            mm_per_tick_assumed=mm_per_tick,
            ticks_detected=int(len(peaks)), spacings_px=[],
            inlier_count=0, inlier_fraction=0.0, inlier_cv=None,
            drift_correlation=None,
            notes="Fewer than 3 ticks detected in the given ROI - not enough "
                  "to measure spacing. Check the ROI actually covers a clean "
                  "tick-mark band.",
        )

    spacings = np.diff(peaks)
    median_spacing = float(np.median(spacings))
    lower = median_spacing * (1 - CALIBRATION_OUTLIER_TOLERANCE)
    upper = median_spacing * (1 + CALIBRATION_OUTLIER_TOLERANCE)
    inlier_mask = (spacings >= lower) & (spacings <= upper)
    inliers = spacings[inlier_mask]
    inlier_positions = np.where(inlier_mask)[0]

    inlier_fraction = len(inliers) / len(spacings)
    inlier_cv = float(inliers.std() / inliers.mean()) if len(inliers) > 0 and inliers.mean() > 0 else None

    # Drift check: a smooth systematic trend (e.g. perspective) can pass
    # the local outlier/CV check above while still being unreliable -
    # each spacing looks fine next to its neighbors, but the sequence
    # trends steadily up or down. Caught via correlation between tick
    # order and spacing value among the inliers.
    drift_correlation = None
    if len(inliers) >= 3:
        if inliers.std() < 1e-9:
            # Perfectly (or near-perfectly) regular spacing - there is no
            # variation for a trend to exist in, so this is the "no drift"
            # case, not an undefined one. Computing corrcoef here would
            # divide by ~0 and produce NaN, which must not be read as "drift
            # detected" (NaN comparisons are always False in Python).
            drift_correlation = 0.0
        else:
            corr_matrix = np.corrcoef(inlier_positions, inliers)
            drift_correlation = float(corr_matrix[0, 1])

    drift_ok = drift_correlation is None or abs(drift_correlation) <= CALIBRATION_MAX_DRIFT_CORRELATION

    validated = (
        inlier_fraction >= CALIBRATION_MIN_INLIER_FRACTION
        and inlier_cv is not None
        and inlier_cv <= CALIBRATION_MAX_CV
        and drift_ok
    )

    if not validated:
        reasons = []
        if inlier_fraction < CALIBRATION_MIN_INLIER_FRACTION:
            reasons.append(f"inlier fraction {inlier_fraction:.2f} < {CALIBRATION_MIN_INLIER_FRACTION}")
        if inlier_cv is not None and inlier_cv > CALIBRATION_MAX_CV:
            reasons.append(f"CV {inlier_cv:.3f} > {CALIBRATION_MAX_CV}")
        if not drift_ok:
            reasons.append(
                f"systematic drift detected (spacing-vs-order correlation "
                f"{drift_correlation:.2f}, exceeds {CALIBRATION_MAX_DRIFT_CORRELATION}) - "
                f"spacing is trending, not just noisy, likely perspective/tilt"
            )
        return CalibrationResult(
            source_name=source_name, axis=axis, roi=roi,
            status="NOT_VALIDATED", px_per_mm=None,
            mm_per_tick_assumed=mm_per_tick,
            ticks_detected=int(len(peaks)), spacings_px=[int(s) for s in spacings],
            inlier_count=int(len(inliers)), inlier_fraction=round(inlier_fraction, 4),
            inlier_cv=round(inlier_cv, 4) if inlier_cv is not None else None,
            drift_correlation=round(drift_correlation, 4) if drift_correlation is not None else None,
            notes=(
                f"Tick spacing did not pass validation ({'; '.join(reasons)}). "
                f"px_per_mm is intentionally not reported - do not use for measurement."
            ),
        )

    inlier_median_spacing_px = float(np.median(inliers))
    px_per_mm = inlier_median_spacing_px / mm_per_tick

    return CalibrationResult(
        source_name=source_name, axis=axis, roi=roi,
        status="VALIDATED_SINGLE_AXIS_PROVISIONAL", px_per_mm=round(px_per_mm, 4),
        mm_per_tick_assumed=mm_per_tick,
        ticks_detected=int(len(peaks)), spacings_px=[int(s) for s in spacings],
        inlier_count=int(len(inliers)), inlier_fraction=round(inlier_fraction, 4),
        inlier_cv=round(inlier_cv, 4),
        drift_correlation=round(drift_correlation, 4) if drift_correlation is not None else None,
        notes=(
            "Validated along ONE axis only, from ONE image, over the specific "
            "pixel range covered by the ROI. Specific to this photo's camera "
            "distance/zoom - not transferable to other images or to other "
            "regions of the same image without a fixed capture distance and "
            "a check that scale doesn't vary across the frame. Ruler-to-mesh "
            "plane offset and lens distortion are not corrected. See "
            "core/calibration.py module docstring for full caveats before "
            "using for measurement."
        ),
    )


def save_calibration_result(result: CalibrationResult, output_dir: Path) -> Path:
    """Save a calibration result as JSON so it can be inspected or
    reused without re-running detection. Never written into 02_DATASET.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(result.source_name).stem
    output_path = output_dir / f"calibration_{stem}_{result.axis}.json"
    with open(output_path, "w") as f:
        json.dump(asdict(result), f, indent=2)
    return output_path
