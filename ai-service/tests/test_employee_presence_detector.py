import unittest

from modules.employee_presence_detector import EmployeePresenceDetector


def _face(employee_id=1, similarity=0.9):
    return {
        "type": "FACE_RESULT",
        "matched": True,
        "employeeId": employee_id,
        "employeeNo": f"E{employee_id:03d}",
        "name": f"Employee {employee_id}",
        "similarity": similarity,
    }


class EmployeePresenceDetectorTests(unittest.TestCase):
    def test_marks_employee_absent_after_timeout(self):
        detector = EmployeePresenceDetector(absence_timeout_seconds=5)

        first_events = detector.detect([_face()], timestamp="2026-07-08T03:00:00+08:00")
        leave_events = detector.detect([], timestamp="2026-07-08T03:00:06+08:00", frame_id="frame-6")

        self.assertEqual(first_events, [])
        self.assertEqual(len(leave_events), 1)
        self.assertEqual(leave_events[0]["type"], "EMPLOYEE_PRESENCE_EVENT")
        self.assertEqual(leave_events[0]["eventType"], "LEAVE")
        self.assertEqual(leave_events[0]["employeeId"], 1)
        self.assertEqual(leave_events[0]["status"], "absent")
        self.assertEqual(leave_events[0]["leaveDurationSeconds"], 6.0)
        self.assertEqual(detector.status()["absentCount"], 1)
        self.assertEqual(detector.status()["presentCount"], 0)

    def test_returns_employee_with_leave_duration(self):
        detector = EmployeePresenceDetector(absence_timeout_seconds=5)

        detector.detect([_face()], timestamp="2026-07-08T03:00:00+08:00")
        detector.detect([], timestamp="2026-07-08T03:00:06+08:00")
        return_events = detector.detect([_face()], timestamp="2026-07-08T03:00:10+08:00", frame_id="frame-10")

        self.assertEqual(len(return_events), 1)
        self.assertEqual(return_events[0]["eventType"], "RETURN")
        self.assertEqual(return_events[0]["status"], "present")
        self.assertEqual(return_events[0]["leaveDurationSeconds"], 10.0)
        self.assertEqual(return_events[0]["leaveStartedAt"], "2026-07-08T03:00:00+08:00")
        self.assertEqual(detector.status()["presentCount"], 1)

    def test_does_not_update_from_unknown_or_low_similarity_faces(self):
        detector = EmployeePresenceDetector(absence_timeout_seconds=5, min_similarity=0.8)

        events = detector.detect(
            [
                {"type": "FACE_RESULT", "matched": False, "employeeId": None},
                _face(employee_id=2, similarity=0.4),
            ],
            timestamp="2026-07-08T03:00:00+08:00",
        )

        self.assertEqual(events, [])
        self.assertEqual(detector.status()["employeeCount"], 0)

    def test_repeated_absent_frames_do_not_duplicate_leave_event(self):
        detector = EmployeePresenceDetector(absence_timeout_seconds=5)

        detector.detect([_face()], timestamp="2026-07-08T03:00:00+08:00")
        first_leave = detector.detect([], timestamp="2026-07-08T03:00:06+08:00")
        second_leave = detector.detect([], timestamp="2026-07-08T03:00:09+08:00")

        self.assertEqual(len(first_leave), 1)
        self.assertEqual(second_leave, [])


if __name__ == "__main__":
    unittest.main()
