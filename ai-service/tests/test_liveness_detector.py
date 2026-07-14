import unittest

import numpy as np

from modules.liveness_detector import LivenessDetector, QUALITY_WARNING


class LivenessDetectorTests(unittest.TestCase):
    def test_disabled_detector_keeps_existing_enrollment_compatible_without_formal_pass(self):
        result = LivenessDetector(enabled=False).predict(np.zeros((80, 80, 3), dtype=np.uint8))
        self.assertFalse(result.available)
        self.assertIsNone(result.passed)
        self.assertEqual(result.provider, "rgb_quality_heuristic")

    def test_quality_heuristic_never_claims_formal_liveness_pass(self):
        result = LivenessDetector(enabled=True, threshold=0.25).predict(np.random.default_rng(1).integers(0, 255, (80, 80, 3), dtype=np.uint8))
        self.assertFalse(result.available)
        self.assertIsNone(result.passed)
        self.assertEqual(result.provider, "rgb_quality_heuristic")
        self.assertTrue(result.quality_heuristic_passed)
        self.assertEqual(result.warning, QUALITY_WARNING)

    def test_missing_onnx_model_is_explicitly_unavailable(self):
        result = LivenessDetector(enabled=True, provider="onnx", model_path="missing.onnx").predict(np.zeros((80, 80, 3), dtype=np.uint8))
        self.assertFalse(result.available)
        self.assertIsNone(result.passed)
        self.assertEqual(result.provider, "onnx")
        self.assertIn("No verified ONNX", result.warning)

    def test_unknown_provider_does_not_silently_fall_back_to_quality_heuristics(self):
        result = LivenessDetector(enabled=True, provider="typo").predict(np.zeros((80, 80, 3), dtype=np.uint8))
        self.assertFalse(result.available)
        self.assertIsNone(result.passed)
        self.assertEqual(result.provider, "typo")
        self.assertIn("Unsupported", result.warning)


if __name__ == "__main__":
    unittest.main()
