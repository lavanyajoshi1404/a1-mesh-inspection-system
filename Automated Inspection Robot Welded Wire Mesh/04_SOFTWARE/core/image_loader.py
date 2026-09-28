"""
Milestone 1 - image loading and basic property inspection.

Scope (deliberately narrow):
  - Read one image file from disk with OpenCV.
  - Report whether it loaded successfully, with a clear error otherwise.
  - Report width, height, channel count, and file format.
  - Save a verification copy so a human can confirm the read was correct.

Explicitly OUT of scope here, per the current project stage:
  - No mesh/wire/intersection detection.
  - No spacing, alignment, or visible-anomaly analysis.
  - No defect or PASS/FAIL decisions of any kind.
  - No physical sample ID or label is assigned to the image - this
    module only reports measurable facts about the file itself.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union

import cv2
import numpy as np

from config.settings import SUPPORTED_EXTENSIONS


class ImageLoadError(Exception):
    """Raised when an image cannot be located, validated, or decoded."""


@dataclass
class ImageInfo:
    """Measurable, factual properties of a successfully loaded image.

    Deliberately holds only facts (dimensions, channel count, file
    format/extension, file size). It does NOT hold or infer any label,
    physical sample ID, quality verdict, or defect information - those
    are outside this milestone's scope and must never be invented here.
    """
    path: Path
    width: int
    height: int
    channels: int
    file_format: str
    file_size_bytes: int


def load_image(path: Union[str, Path]) -> Tuple[np.ndarray, ImageInfo]:
    """Load a single image from disk and report its basic properties.

    Args:
        path: Path to the image file.

    Returns:
        A tuple of (image array as read by OpenCV in BGR order, ImageInfo).

    Raises:
        ImageLoadError: if the path does not exist, is not a file, has
            an unsupported extension, or OpenCV cannot decode it.
    """
    image_path = Path(path)

    if not image_path.exists():
        raise ImageLoadError(f"File not found: {image_path}")

    if not image_path.is_file():
        raise ImageLoadError(f"Path is not a file: {image_path}")

    extension = image_path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ImageLoadError(
            f"Unsupported file extension '{extension}' for {image_path.name}. "
            f"Supported extensions: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    # cv2.imread returns None on decode failure rather than raising, so
    # we must check explicitly - trusting an exception here would miss
    # corrupted/truncated files silently.
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)

    if image is None:
        raise ImageLoadError(
            f"OpenCV could not decode image: {image_path}. "
            f"The file may be corrupted or not a valid image."
        )

    height, width = image.shape[:2]
    channels = image.shape[2] if image.ndim == 3 else 1

    info = ImageInfo(
        path=image_path,
        width=width,
        height=height,
        channels=channels,
        file_format=extension.lstrip("."),
        file_size_bytes=image_path.stat().st_size,
    )

    return image, info


def save_verification_copy(image: np.ndarray, source_path: Path, output_dir: Path) -> Path:
    """Save a copy of the loaded image so a human can confirm the read.

    This writes only to `output_dir`. It never overwrites, renames, or
    otherwise modifies the original dataset file.

    Returns:
        The path the verification copy was written to.

    Raises:
        ImageLoadError: if the copy could not be written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"verified_{source_path.name}"
    success = cv2.imwrite(str(output_path), image)

    if not success:
        raise ImageLoadError(f"Failed to write verification copy to {output_path}")

    return output_path
