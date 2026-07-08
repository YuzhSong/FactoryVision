import unittest

import numpy as np

from modules.liveness_detector import LivenessDetector


class LivenessDetectorTests(unittest.TestCase):
    def test_disabled_detector_always_passes(self):
        detector = LivenessDetector(enabled=False)

        result = detector.predict(np.zeros((80, 80, 3), dtype=np.uint8))

        self.assertTrue(result.passed)
        self.assertEqual(result.method, "disabled")

    def test_uniform_flat_crop_is_rejected(self):
        detector = LivenessDetector(enabled=True, threshold=0.55, min_face_size=48)

        result = detector.predict(np.full((80, 80, 3), 128, dtype=np.uint8))

        self.assertFalse(result.passed)
        self.assertEqual(result.reject_reason, "liveness_failed")
        self.assertLess(result.score, 0.55)

    def test_textured_rgb_crop_can_pass_heuristic_threshold(self):
        detector = LivenessDetector(enabled=True, threshold=0.25, min_face_size=48)
        rng = np.random.default_rng(123)
        textured = rng.integers(0, 255, size=(80, 80, 3), dtype=np.uint8)

        result = detector.predict(textured)

        self.assertTrue(result.passed)
        self.assertGreaterEqual(result.score, 0.25)

    def test_small_face_crop_is_rejected(self):
        detector = LivenessDetector(enabled=True, min_face_size=48)

        result = detector.predict(np.zeros((32, 32, 3), dtype=np.uint8))

        self.assertFalse(result.passed)
        self.assertEqual(result.reject_reason, "face_too_small_for_liveness")


if __name__ == "__main__":
    unittest.main()
