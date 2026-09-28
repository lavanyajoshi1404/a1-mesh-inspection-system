"""
Milestone 2 tests for core.preprocessing.

Self-contained: uses synthetic images (no dependency on the real
dataset being present at a fixed path), except where noted.

Run with:
    python -m unittest discover -s tests
(from the 04_SOFTWARE/ directory)
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.preprocessing import PreprocessingError, preprocess_image


def _make_synthetic_mesh_image(height=800, width=600):
    """A small synthetic grid image: light background, dark grid lines.

    Stands in for a real wire-mesh photo without depending on one being
    present on disk - bright background with darker crossing lines is
    enough to exercise resize/grayscale/threshold/edge logic.
    """
    img = np.full((height, width, 3), 200, dtype=np.uint8)
    for y in range(0, height, 80):
        cv2.line(img, (0, y), (width, y), (60, 60, 60), 6)
    for x in range(0, width, 80):
        cv2.line(img, (x, 0), (x, height), (60, 60, 60), 6)
    return img


class TestPreprocessing(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.output_dir = self.tmp_dir / "processed"
        self.image = _make_synthetic_mesh_image()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_valid_image_preprocesses_successfully(self):
        result = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir, save_intermediate=True
        )
        self.assertEqual(result.original_width, 600)
        self.assertEqual(result.original_height, 800)
        self.assertGreater(result.otsu_threshold, 0)

    def test_missing_input_raises_clear_error(self):
        with self.assertRaises(PreprocessingError):
            preprocess_image(None, "missing.jpg", self.output_dir)

    def test_empty_array_raises_clear_error(self):
        empty = np.array([])
        with self.assertRaises(PreprocessingError):
            preprocess_image(empty, "empty.jpg", self.output_dir)

    def test_save_intermediate_requires_output_dir(self):
        with self.assertRaises(PreprocessingError):
            preprocess_image(self.image, "synthetic.jpg", output_dir=None, save_intermediate=True)

    def test_resize_respects_max_dimension_and_downscales_only(self):
        # Image is 800x600 (long side 800); cap well below that.
        result = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir,
            max_dimension=400, save_intermediate=False,
        )
        self.assertEqual(max(result.processed_width, result.processed_height), 400)
        self.assertLess(result.resize_scale, 1.0)

        # Cap ABOVE the image's long side - must NOT upscale.
        result_no_upscale = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir,
            max_dimension=5000, save_intermediate=False,
        )
        self.assertEqual(result_no_upscale.processed_width, 600)
        self.assertEqual(result_no_upscale.processed_height, 800)
        self.assertEqual(result_no_upscale.resize_scale, 1.0)

    def test_resize_disabled_with_none_keeps_original_size(self):
        result = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir,
            max_dimension=None, save_intermediate=False,
        )
        self.assertEqual(result.processed_width, 600)
        self.assertEqual(result.processed_height, 800)
        self.assertEqual(result.resize_scale, 1.0)

    def test_intermediate_outputs_are_saved_and_readable(self):
        result = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir, save_intermediate=True
        )
        expected_steps = {"grayscale", "denoised", "enhanced", "threshold", "edges"}
        self.assertEqual(set(result.output_paths.keys()), expected_steps)

        for step_name, path in result.output_paths.items():
            self.assertTrue(path.exists(), f"{step_name} output missing on disk")
            saved = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            self.assertIsNotNone(saved, f"{step_name} output not readable by OpenCV")
            # All saved outputs are single-channel (grayscale/binary/edges).
            self.assertEqual(saved.ndim, 2, f"{step_name} output should be single-channel")

    def test_no_files_written_when_save_intermediate_false(self):
        preprocess_image(
            self.image, "synthetic.jpg", self.output_dir, save_intermediate=False
        )
        self.assertFalse(self.output_dir.exists())

    def test_original_image_array_not_modified(self):
        original_copy = self.image.copy()
        preprocess_image(self.image, "synthetic.jpg", self.output_dir, save_intermediate=False)
        np.testing.assert_array_equal(self.image, original_copy)

    def test_pipeline_is_deterministic(self):
        result_a = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir / "a", save_intermediate=True
        )
        result_b = preprocess_image(
            self.image, "synthetic.jpg", self.output_dir / "b", save_intermediate=True
        )
        self.assertEqual(result_a.otsu_threshold, result_b.otsu_threshold)
        self.assertEqual(result_a.processed_width, result_b.processed_width)
        self.assertEqual(result_a.processed_height, result_b.processed_height)

        for step_name in result_a.output_paths:
            img_a = cv2.imread(str(result_a.output_paths[step_name]), cv2.IMREAD_UNCHANGED)
            img_b = cv2.imread(str(result_b.output_paths[step_name]), cv2.IMREAD_UNCHANGED)
            np.testing.assert_array_equal(
                img_a, img_b, err_msg=f"{step_name} output differs between identical runs"
            )


if __name__ == "__main__":
    unittest.main()
