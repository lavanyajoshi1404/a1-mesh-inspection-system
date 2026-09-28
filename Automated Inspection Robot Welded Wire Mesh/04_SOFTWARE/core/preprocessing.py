"""
Milestone 2 - image preprocessing.

Prepares a loaded image for the (future, not-yet-implemented) mesh/wire
detection stage. Every operation here was chosen because a measurement
taken on a real dataset image justified it - see the Milestone 2 audit
notes for the numbers. This module does NOT detect wires, intersections,
or anomalies, and does not make any PASS/FAIL or calibration decision.

Pipeline:
    resize (configurable, downscale-only)
      -> grayscale
      -> light edge-preserving denoise (bilateral filter)
      -> local contrast correction (CLAHE)
      -> Otsu threshold  (data-derived split point, not a hardcoded guess)
      -> Canny edges     (hysteresis bounds derived from the Otsu value)

This module is intentionally independent of core/image_loader.py's
concerns (file I/O, format validation) and of any future mesh-detection
module - it only transforms an already-loaded image array and reports
what it did.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from config.settings import (
    PREPROCESS_BILATERAL_DIAMETER,
    PREPROCESS_BILATERAL_SIGMA_COLOR,
    PREPROCESS_BILATERAL_SIGMA_SPACE,
    PREPROCESS_CLAHE_CLIP_LIMIT,
    PREPROCESS_CLAHE_TILE_GRID,
    PREPROCESS_MAX_DIMENSION,
)


class PreprocessingError(Exception):
    """Raised when preprocessing cannot be performed on the given input."""


@dataclass
class PreprocessingResult:
    """Structured, factual record of what preprocessing did.

    Holds only measurable facts about the transformation performed
    (sizes, the Otsu threshold value it found, where outputs were
    written). It does not hold or infer any label, sample ID, quality
    verdict, or defect information.
    """
    source_name: str
    original_width: int
    original_height: int
    processed_width: int
    processed_height: int
    resize_scale: float          # 1.0 means no resize was applied
    otsu_threshold: float        # value Otsu's method found for THIS image
    output_paths: Dict[str, Path] = field(default_factory=dict)


def _resize_if_needed(image: np.ndarray, max_dimension: Optional[int]) -> Tuple[np.ndarray, float]:
    """Downscale so the longer side is at most `max_dimension`.

    Never upscales (a scale > 1.0 would fabricate detail that isn't in
    the source). Returns the (possibly unchanged) image and the scale
    factor actually applied.
    """
    if max_dimension is None:
        return image, 1.0

    height, width = image.shape[:2]
    longer_side = max(height, width)

    if longer_side <= max_dimension:
        return image, 1.0

    scale = max_dimension / longer_side
    new_size = (int(round(width * scale)), int(round(height * scale)))
    resized = cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)
    return resized, scale


def preprocess_image(
    image: np.ndarray,
    source_name: str,
    output_dir: Optional[Path] = None,
    max_dimension: Optional[int] = PREPROCESS_MAX_DIMENSION,
    save_intermediate: bool = True,
) -> PreprocessingResult:
    """Run the Milestone 2 preprocessing pipeline on a loaded image.

    Args:
        image: Image array as returned by core.image_loader.load_image
            (BGR, as read by OpenCV). The original array is never
            modified in place.
        source_name: Name used to prefix any saved output files (e.g.
            the original filename's stem). Not a path - this function
            never reads or writes the original file.
        output_dir: Directory to save intermediate outputs to. Required
            if save_intermediate is True. Never the original dataset
            directory - caller is responsible for pointing this at a
            processed/ output location.
        max_dimension: Longest-side cap in pixels for the downscale
            step, or None to skip resizing entirely. See
            config/settings.py for the measurement behind the default.
        save_intermediate: Whether to write intermediate step outputs
            to disk. Set False for fast, file-free unit testing.

    Returns:
        A PreprocessingResult describing what was done.

    Raises:
        PreprocessingError: if the input image is missing/empty, or if
            save_intermediate is True but no output_dir was given.
    """
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise PreprocessingError("preprocess_image received an empty or invalid image array.")

    if save_intermediate and output_dir is None:
        raise PreprocessingError("output_dir is required when save_intermediate=True.")

    original_height, original_width = image.shape[:2]

    # 1. Resize (downscale-only, configurable - see settings for rationale)
    resized, scale = _resize_if_needed(image, max_dimension)
    processed_height, processed_width = resized.shape[:2]

    # 2. Grayscale - justified: the wire-vs-background separation in
    # this dataset is a luminance problem (see histogram analysis).
    if resized.ndim == 3:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    else:
        gray = resized

    # 3. Light, edge-preserving noise reduction. Deliberately mild -
    # measured background noise on the sample image was low, so this is
    # not a heavy denoiser, just enough to steady the input to CLAHE
    # and Canny below.
    denoised = cv2.bilateralFilter(
        gray,
        d=PREPROCESS_BILATERAL_DIAMETER,
        sigmaColor=PREPROCESS_BILATERAL_SIGMA_COLOR,
        sigmaSpace=PREPROCESS_BILATERAL_SIGMA_SPACE,
    )

    # 4. Local contrast correction (CLAHE) - justified by measured
    # ~75-unit corner-to-corner brightness variation (uneven lighting).
    clahe = cv2.createCLAHE(
        clipLimit=PREPROCESS_CLAHE_CLIP_LIMIT,
        tileGridSize=PREPROCESS_CLAHE_TILE_GRID,
    )
    enhanced = clahe.apply(denoised)

    # 5. Threshold preparation - Otsu's method picks the split point
    # from this image's own histogram; nothing is hardcoded or assumed.
    otsu_value, threshold_image = cv2.threshold(
        enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # 6. Edge preparation - Canny, with hysteresis bounds derived from
    # the Otsu value rather than picked arbitrarily.
    canny_low = max(0, int(0.5 * otsu_value))
    canny_high = max(canny_low + 1, int(otsu_value))
    edges = cv2.Canny(enhanced, canny_low, canny_high)

    result = PreprocessingResult(
        source_name=source_name,
        original_width=original_width,
        original_height=original_height,
        processed_width=processed_width,
        processed_height=processed_height,
        resize_scale=scale,
        otsu_threshold=float(otsu_value),
    )

    if save_intermediate:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(source_name).stem
        steps = {
            "grayscale": gray,
            "denoised": denoised,
            "enhanced": enhanced,
            "threshold": threshold_image,
            "edges": edges,
        }
        for step_name, step_image in steps.items():
            out_path = output_dir / f"preprocessed_{stem}_{step_name}.jpg"
            success = cv2.imwrite(str(out_path), step_image)
            if not success:
                raise PreprocessingError(f"Failed to write {step_name} output to {out_path}")
            result.output_paths[step_name] = out_path

    return result
