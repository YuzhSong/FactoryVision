import unittest

from modules.stranger_detector import StrangerDetector


class StrangerDetectorTests(unittest.TestCase):
    """Test stranger confirmation and cooldown behavior."""

    def test_unknown_face_requires_confirmed_frames(self):
        detector = StrangerDetector(confirm_frames=3, cooldown_seconds=30)
        unknown_face = {
            "type": "FACE_RESULT",
            "matched": False,
            "similarity": 0.22,
            "threshold": 0.45,
            "faceBox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
        }

        first = detector.detect([unknown_face], camera_id=1, frame_id="f1", timestamp="2026-07-08T10:00:00+08:00")
        second = detector.detect([unknown_face], camera_id=1, frame_id="f2", timestamp="2026-07-08T10:00:01+08:00")
        third = detector.detect([unknown_face], camera_id=1, frame_id="f3", timestamp="2026-07-08T10:00:02+08:00")

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(len(third), 1)
        self.assertEqual(third[0]["type"], "STRANGER_ALERT")
        self.assertEqual(third[0]["observedFrames"], 3)

    def test_cooldown_suppresses_repeated_alerts(self):
        detector = StrangerDetector(confirm_frames=1, cooldown_seconds=30)
        unknown_face = {
            "type": "FACE_RESULT",
            "matched": False,
            "faceBox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
        }

        first = detector.detect([unknown_face], camera_id=1, frame_id="f1", timestamp="2026-07-08T10:00:00+08:00")
        second = detector.detect([unknown_face], camera_id=1, frame_id="f2", timestamp="2026-07-08T10:00:10+08:00")
        third = detector.detect([unknown_face], camera_id=1, frame_id="f3", timestamp="2026-07-08T10:00:31+08:00")

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])
        self.assertEqual(len(third), 1)

    def test_known_face_does_not_trigger_stranger_alert(self):
        detector = StrangerDetector(confirm_frames=1)
        known_face = {
            "type": "FACE_RESULT",
            "matched": True,
            "employeeId": 1,
            "faceBox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
        }

        alerts = detector.detect([known_face], camera_id=1, frame_id="f1", timestamp="2026-07-08T10:00:00+08:00")

        self.assertEqual(alerts, [])


if __name__ == "__main__":
    unittest.main()
