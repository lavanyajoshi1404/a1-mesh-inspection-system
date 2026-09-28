"""
CLI entry point for Milestone 1 (load/verify) and Milestone 2
(preprocessing), combined so there is one coherent command rather than
duplicate entry points.

Run:
    python main.py path/to/image.jpg                # Milestone 1 only
    python main.py path/to/image.jpg --show           # + preview window
    python main.py path/to/image.jpg --preprocess      # + Milestone 2 pipeline

Default behavior (no flags) is unchanged from Milestone 1: load, report
properties, save a verification copy. --preprocess is purely additive -
it runs after the Milestone 1 steps and does not alter them.

This is a thin CLI wrapper around core/image_loader.py and
core/preprocessing.py, deliberately kept separate from dashboard/
(empty for now) so the image-processing logic never becomes entangled
with UI code.

Note on --show: on a machine with no display attached (a headless
server, an SSH session, most CI runners, this evaluation sandbox),
cv2.imshow does not fail gracefully with a catchable Python exception -
it can hard-abort the whole process. So display is opt-in via --show
rather than attempted automatically; leave it off unless you're running
this on your own desktop.
"""

import os
import sys
from pathlib import Path

from config.settings import DATA_PROCESSED_DIR
from core.image_loader import ImageLoadError, load_image, save_verification_copy
from core.preprocessing import PreprocessingError, preprocess_image


def main(argv: list) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    show_requested = "--show" in argv
    preprocess_requested = "--preprocess" in argv

    if len(args) != 1:
        print("Usage: python main.py <path-to-image> [--show] [--preprocess]")
        return 2

    image_path = Path(args[0])

    try:
        image, info = load_image(image_path)
    except ImageLoadError as e:
        print(f"[FAIL] Could not load image: {e}")
        return 1

    print("[OK] Image loaded successfully.")
    print(f"  Path:       {info.path}")
    print(f"  Format:     {info.file_format}")
    print(f"  Width:      {info.width} px")
    print(f"  Height:     {info.height} px")
    print(f"  Channels:   {info.channels}")
    print(f"  File size:  {info.file_size_bytes:,} bytes")

    try:
        output_path = save_verification_copy(image, info.path, DATA_PROCESSED_DIR)
        print(f"[OK] Verification copy saved to: {output_path}")
    except ImageLoadError as e:
        print(f"[FAIL] Could not save verification copy: {e}")
        return 1

    if preprocess_requested:
        print()
        print("[INFO] Running Milestone 2 preprocessing pipeline...")
        try:
            result = preprocess_image(image, info.path.name, DATA_PROCESSED_DIR)
        except PreprocessingError as e:
            print(f"[FAIL] Preprocessing failed: {e}")
            return 1

        print("[OK] Preprocessing complete.")
        print(f"  Original size:   {result.original_width} x {result.original_height}")
        print(f"  Processed size:  {result.processed_width} x {result.processed_height}")
        print(f"  Resize scale:    {result.resize_scale:.4f}")
        print(f"  Otsu threshold:  {result.otsu_threshold}")
        for step_name, path in result.output_paths.items():
            print(f"  {step_name:<10} -> {path}")

    if not show_requested:
        print()
        print("[INFO] Skipping interactive preview (pass --show to open one). "
              "The saved copy above is the verification result.")
        return 0

    if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
        print("[INFO] --show was requested but no display was detected "
              "(DISPLAY is not set). Skipping preview - the saved copy "
              "above is still a valid verification result.")
        return 0

    import cv2  # imported here, only needed for the optional preview path
    cv2.imshow(f"Milestone 1 - {info.path.name}", image)
    print("Press any key in the image window to close it...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
