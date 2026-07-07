import unittest

from modules.running_detector import RunningDetector


class RunningDetectorTests(unittest.TestCase):
    def test_detect_supports_iso_timestamps(self):
        detector = RunningDetector(speed_threshold=15.0, confirm_frames=2)
        history = [
            {
                "trackId": "t-1",
                "centerPoint": {"x": 0, "y": 0},
                "timestamp": "2026-07-07T10:00:00+08:00",
            },
            {
                "trackId": "t-1",
                "centerPoint": {"x": 20, "y": 0},
                "timestamp": "2026-07-07T10:00:01+08:00",
            },
        ]

        result = detector.detect(history)

        self.assertIsNotNone(result)
        self.assertTrue(result["isRunning"])
        self.assertEqual(result["pixelSpeed"], 20.0)

    def test_detect_falls_back_to_frame_index_and_fps(self):
        detector = RunningDetector(speed_threshold=15.0, confirm_frames=2)
        history = [
            {
                "trackId": "t-1",
                "centerPoint": {"x": 0, "y": 0},
                "frameIndex": 0,
                "fps": 10,
            },
            {
                "trackId": "t-1",
                "centerPoint": {"x": 5, "y": 0},
                "frameIndex": 10,
                "fps": 10,
            },
        ]

        result = detector.detect(history)

        self.assertIsNotNone(result)
        self.assertFalse(result["isRunning"])
        self.assertEqual(result["pixelSpeed"], 5.0)


if __name__ == "__main__":
    unittest.main()
