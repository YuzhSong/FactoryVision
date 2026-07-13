import unittest

from modules.employee_recognition_detector import EmployeeRecognitionDetector


def _face(track_id="t1", employee_id=4):
    return {
        "type": "FACE_RESULT",
        "trackId": track_id,
        "employeeId": employee_id,
        "name": "Employee 4",
        "matched": True,
        "similarity": 0.8,
        "threshold": 0.45,
    }


class EmployeeRecognitionDetectorTests(unittest.TestCase):
    def test_continuous_track_emits_once(self):
        detector = EmployeeRecognitionDetector(employee_cooldown_seconds=60, track_ttl_seconds=30)
        first = detector.detect([_face()], camera_id=1, timestamp="2026-07-12T10:00:00+08:00")
        repeated = detector.detect([_face()], camera_id=1, timestamp="2026-07-12T10:00:40+08:00")
        self.assertEqual([item["eventType"] for item in first], ["face_recognized"])
        self.assertEqual(first[0]["name"], "Employee 4")
        self.assertEqual(first[0]["confidence"], 0.8)
        self.assertEqual(first[0]["description"], "Employee 4 置信度 80.0%")
        self.assertEqual(repeated, [])

    def test_fragmented_track_uses_camera_employee_cooldown(self):
        detector = EmployeeRecognitionDetector(employee_cooldown_seconds=60, track_ttl_seconds=30)
        detector.detect([_face("t1")], camera_id=1, timestamp="2026-07-12T10:00:00+08:00")
        suppressed = detector.detect([_face("t2")], camera_id=1, timestamp="2026-07-12T10:00:59+08:00")
        allowed = detector.detect([_face("t3")], camera_id=1, timestamp="2026-07-12T10:01:00+08:00")
        other_camera = detector.detect([_face("t1")], camera_id=2, timestamp="2026-07-12T10:00:10+08:00")
        self.assertEqual(suppressed, [])
        self.assertEqual(len(allowed), 1)
        self.assertEqual(len(other_camera), 1)

    def test_unknown_never_emits(self):
        detector = EmployeeRecognitionDetector()
        unknown = _face()
        unknown.update({"matched": False, "employeeId": None})
        self.assertEqual(detector.detect([unknown], camera_id=1), [])


if __name__ == "__main__":
    unittest.main()
