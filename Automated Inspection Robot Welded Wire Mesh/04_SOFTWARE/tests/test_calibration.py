"""
Milestone 3 tests for core.calibration.

Uses synthetic ruler-like images (regularly spaced dark ticks on a
light background) so tests don't depend on the real dataset being
present at a fixed path. The real-image validation run (against the
actual 49-image dataset) is done separately and reported in the
milestone writeup, not here.

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

from core.calibration import CalibrationError, calibrate_from_ruler, save_calibration_result


def _make_synthetic_ruler(height=1000, width=200, tick_spacing_px=20, tick_thickness=2):
    """A vertical strip with clean, perfectly regular dark ticks -
    stands in for a well-isolated ruler tick band."""
    img = np.full((height, width, 3), 220, dtype=np.uint8)
    y = 0
    while y < height:
        cv2.line(img, (20, y), (width - 20, y), (10, 10, 10), tick_thickness)
        y += tick_spacing_px
    return img


def _make_noisy_ruler(height=1000, width=200):
    """Irregular dark marks at random spacing - stands in for a band
    that should NOT pass calibration validation (e.g. text/logo
    interference, or a band that isn't actually a clean tick strip)."""
    rng = np.random.default_rng(42)
    img = np.full((height, width, 3), 220, dtype=np.uint8)
    y = 0
    while y < height:
        cv2.line(img, (20, y), (width - 20, y), (10, 10, 10), 2)
        y += int(rng.integers(8, 60))  # wildly irregular spacing
    return img


class TestCalibration(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_clean_regular_ticks_are_validated(self):
        img = _make_synthetic_ruler(tick_spacing_px=20)
        result = calibrate_from_ruler(
            img, "synthetic_ruler.jpg", roi=(0, 200, 0, 1000), axis="vertical"
        )
        self.assertEqual(result.status, "VALIDATED_SINGLE_AXIS_PROVISIONAL")
        self.assertIsNotNone(result.px_per_mm)
        # Perfectly regular 20px ticks at 1mm/tick -> ~20 px/mm.
        self.assertAlmostEqual(result.px_per_mm, 20.0, delta=0.5)
        self.assertGreaterEqual(result.inlier_fraction, 0.8)

    def test_irregular_ticks_are_not_validated(self):
        img = _make_noisy_ruler()
        result = calibrate_from_ruler(
            img, "noisy_ruler.jpg", roi=(0, 200, 0, 1000), axis="vertical"
        )
        self.assertEqual(result.status, "NOT_VALIDATED")
        self.assertIsNone(result.px_per_mm)

    def test_too_few_ticks_is_not_validated(self):
        img = np.full((100, 200, 3), 220, dtype=np.uint8)
        cv2.line(img, (20, 50), (180, 50), (10, 10, 10), 2)  # only 1 tick
        result = calibrate_from_ruler(img, "sparse.jpg", roi=(0, 200, 0, 100), axis="vertical")
        self.assertEqual(result.status, "NOT_VALIDATED")
        self.assertIsNone(result.px_per_mm)
        self.assertIn("Fewer than 3 ticks", result.notes)

    def test_empty_image_raises(self):
        with self.assertRaises(CalibrationError):
            calibrate_from_ruler(None, "missing.jpg", roi=(0, 10, 0, 10))

    def test_roi_out_of_bounds_raises(self):
        img = _make_synthetic_ruler()
        with self.assertRaises(CalibrationError):
            calibrate_from_ruler(img, "bad_roi.jpg", roi=(0, 9999, 0, 9999))

    def test_invalid_axis_raises(self):
        img = _make_synthetic_ruler()
        with self.assertRaises(CalibrationError):
            calibrate_from_ruler(img, "bad_axis.jpg", roi=(0, 200, 0, 1000), axis="diagonal")

    def test_horizontal_axis_works(self):
        # Build a horizontal-tick version by transposing the vertical one.
        # Transpose swaps dimensions: (height=200,width=1000) -> (height=1000,width=200).
        vertical = _make_synthetic_ruler(height=200, width=1000, tick_spacing_px=20)
        horizontal = cv2.transpose(vertical)
        self.assertEqual(horizontal.shape[:2], (1000, 200))  # sanity check on the fixture itself
        result = calibrate_from_ruler(
            horizontal, "synthetic_h_ruler.jpg", roi=(0, 200, 0, 1000), axis="horizontal"
        )
        self.assertEqual(result.status, "VALIDATED_SINGLE_AXIS_PROVISIONAL")
        self.assertAlmostEqual(result.px_per_mm, 20.0, delta=0.5)

    def test_save_calibration_result_writes_readable_json(self):
        img = _make_synthetic_ruler()
        result = calibrate_from_ruler(img, "synthetic_ruler.jpg", roi=(0, 200, 0, 1000))
        output_path = save_calibration_result(result, self.tmp_dir)
        self.assertTrue(output_path.exists())

        import json
        with open(output_path) as f:
            data = json.load(f)
        self.assertEqual(data["status"], "VALIDATED_SINGLE_AXIS_PROVISIONAL")
        self.assertIn("px_per_mm", data)

    def test_result_never_reports_plain_calibrated_status(self):
        # Guards against accidentally overclaiming in future edits.
        img = _make_synthetic_ruler()
        result = calibrate_from_ruler(img, "synthetic_ruler.jpg", roi=(0, 200, 0, 1000))
        self.assertNotEqual(result.status, "CALIBRATED")

    def test_smooth_drift_is_rejected_even_with_low_local_noise(self):
        """A systematic drift (e.g. perspective) can look fine locally -
        each spacing close to its neighbors - while still being globally
        unreliable. This must be caught even though it would pass a
        pure outlier/CV check. Found via a real dataset image where one
        ROI's spacing climbed smoothly 27px -> 34px yet had CV ~7%."""
        height, width = 1000, 200
        img = np.full((height, width, 3), 220, dtype=np.uint8)
        y = 0
        spacing = 20.0
        while y < height - 10:
            cv2.line(img, (20, int(y)), (width - 20, int(y)), (10, 10, 10), 2)
            spacing += 0.6  # smooth drift, ~30% over the frame, tiny step-to-step
            y += spacing
        result = calibrate_from_ruler(img, "drifting_ruler.jpg", roi=(0, 200, 0, height), axis="vertical")
        self.assertEqual(result.status, "NOT_VALIDATED")
        self.assertIsNone(result.px_per_mm)
        self.assertIn("drift", result.notes.lower())

    def test_perfectly_regular_ticks_do_not_false_positive_on_drift(self):
        """Regression test: perfectly uniform spacing has ~zero variance,
        which must not make the drift correlation compute as NaN (NaN
        comparisons are always False in Python, which would have
        incorrectly failed validation for the *cleanest* possible input -
        this exact bug was caught when this test was written)."""
        img = _make_synthetic_ruler(tick_spacing_px=20)
        result = calibrate_from_ruler(img, "perfect_ruler.jpg", roi=(0, 200, 0, 1000))
        self.assertEqual(result.status, "VALIDATED_SINGLE_AXIS_PROVISIONAL")
        self.assertEqual(result.drift_correlation, 0.0)


if __name__ == "__main__":
    unittest.main()
