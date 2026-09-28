"""
Milestone 1 tests for core.image_loader.

Self-contained on purpose: these generate a tiny synthetic image rather
than depending on the real 49-image dataset being present at a fixed
path, so they run the same way on any machine.

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

# Allow running this file directly (python tests/test_image_loader.py)
# as well as via unittest discovery from 04_SOFTWARE/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.image_loader import ImageLoadError, load_image, save_verification_copy


class TestImageLoader(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

        # A small synthetic image - enough to exercise a real OpenCV
        # encode/decode round trip without depending on real dataset files.
        self.valid_image_path = self.tmp_dir / "synthetic.jpg"
        synthetic = np.full((120, 160, 3), 200, dtype=np.uint8)
        cv2.imwrite(str(self.valid_image_path), synthetic)

        self.corrupted_image_path = self.tmp_dir / "corrupted.jpg"
        self.corrupted_image_path.write_bytes(b"not a real jpeg")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_load_valid_image_reports_correct_properties(self):
        image, info = load_image(self.valid_image_path)
        self.assertEqual(info.width, 160)
        self.assertEqual(info.height, 120)
        self.assertEqual(info.channels, 3)
        self.assertEqual(info.file_format, "jpg")
        self.assertEqual(image.shape[1], 160)
        self.assertEqual(image.shape[0], 120)

    def test_missing_file_raises(self):
        with self.assertRaises(ImageLoadError):
            load_image(self.tmp_dir / "does_not_exist.jpg")

    def test_unsupported_extension_raises(self):
        bad_ext_path = self.tmp_dir / "image.bmp"
        bad_ext_path.write_bytes(b"irrelevant")
        with self.assertRaises(ImageLoadError):
            load_image(bad_ext_path)

    def test_corrupted_file_raises(self):
        with self.assertRaises(ImageLoadError):
            load_image(self.corrupted_image_path)

    def test_save_verification_copy_writes_file(self):
        image, info = load_image(self.valid_image_path)
        output_dir = self.tmp_dir / "processed"
        output_path = save_verification_copy(image, info.path, output_dir)
        self.assertTrue(output_path.exists())
        self.assertTrue(output_path.name.startswith("verified_"))


if __name__ == "__main__":
    unittest.main()
