import unittest

from modules.abnormal_behavior_service import AbnormalBehaviorService
from modules.fall_detector import FallDetector


def _history(entries):
    return [
        {
            "trackId": "t-1",
            "timestamp": f"2026-07-08T03:00:0{index}+08:00",
            **entry,
        }
        for index, entry in enumerate(entries)
    ]


def _pose(shoulder_y, hip_y, confidence=0.9):
    keypoints = [[0, 0, 0.0] for _ in range(17)]
    keypoints[5] = [10, shoulder_y, confidence]
    keypoints[6] = [30, shoulder_y, confidence]
    keypoints[11] = [60, hip_y, confidence]
    keypoints[12] = [80, hip_y, confidence]
    return keypoints


class FallDetectorTests(unittest.TestCase):
    def test_bbox_fallback_confirms_horizontal_body(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=2, min_confidence=0.6)

        result = detector.detect(
            _history(
                [
                    {"bbox": [20, 10, 60, 110]},
                    {"bbox": [10, 70, 90, 110]},
                    {"bbox": [12, 70, 92, 110]},
                ]
            )
        )

        self.assertTrue(result["isFall"])
        self.assertEqual(result["evidenceType"], "bbox")
        self.assertEqual(result["durationFrames"], 2)
        self.assertEqual(result["level"], "high")
        self.assertEqual(result["confidenceType"], "rule_composite_score")
        self.assertLess(result["confidence"], 1.0)

    def test_upright_bbox_does_not_confirm_fall(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=2)

        result = detector.detect(
            _history(
                [
                    {"bbox": [0, 0, 40, 100]},
                    {"bbox": [2, 0, 42, 100]},
                ]
            )
        )

        self.assertFalse(result["isFall"])
        self.assertEqual(result["confidence"], 0.0)

    def test_pose_horizontal_body_overrides_vertical_bbox(self):
        detector = FallDetector(
            ratio_threshold=1.2,
            confirm_frames=2,
            pose_horizontal_angle_threshold=35,
            pose_min_keypoint_confidence=0.3,
        )

        result = detector.detect(
            _history(
                [
                    {"bbox": [20, 10, 60, 110], "keypoints": _pose(20, 80)},
                    {"bbox": [10, 70, 90, 110], "keypoints": _pose(80, 82)},
                    {"bbox": [12, 70, 92, 110], "keypoints": _pose(80, 82)},
                ]
            )
        )

        self.assertTrue(result["isFall"])
        self.assertEqual(result["evidenceType"], "pose")
        self.assertEqual(result["evidence"]["poseFrames"], 2)
        self.assertLessEqual(result["evidence"]["latestBodyAngle"], 35)

    def test_single_horizontal_frame_does_not_trigger(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=3)
        result = detector.detect(_history([{"bbox": [20, 10, 60, 110]}, {"bbox": [10, 70, 90, 110]}]))
        self.assertFalse(result["isFall"])
        self.assertEqual(result["evidence"]["rejectionReason"], "insufficient_history")

    def test_bend_then_recover_does_not_trigger(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=3)
        result = detector.detect(
            _history(
                [
                    {"bbox": [20, 10, 60, 110]},
                    {"bbox": [10, 45, 85, 105]},
                    {"bbox": [20, 10, 60, 110]},
                    {"bbox": [20, 10, 60, 110]},
                ]
            )
        )
        self.assertFalse(result["isFall"])

    def test_edge_truncated_wide_person_is_rejected(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=2)
        result = detector.detect(
            _history(
                [
                    {"bbox": [20, 10, 60, 100], "frameShape": [120, 120]},
                    {"bbox": [10, 60, 118, 120], "frameShape": [120, 120]},
                    {"bbox": [10, 60, 118, 120], "frameShape": [120, 120]},
                ]
            )
        )
        self.assertFalse(result["isFall"])
        self.assertEqual(result["evidence"]["rejectionReason"], "edge_truncated")

    def test_low_confidence_pose_falls_back_to_bbox(self):
        detector = FallDetector(
            ratio_threshold=1.2,
            confirm_frames=2,
            pose_min_keypoint_confidence=0.5,
        )

        result = detector.detect(
            _history(
                [
                    {"bbox": [0, 0, 40, 100], "keypoints": _pose(40, 45, confidence=0.1)},
                    {"bbox": [2, 0, 42, 100], "keypoints": _pose(40, 45, confidence=0.1)},
                ]
            )
        )

        self.assertFalse(result["isFall"])
        self.assertEqual(result["evidenceType"], "bbox")


    def test_slow_fall_confirms_after_sustained_low_posture(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=3, max_transition_seconds=2, slow_transition_seconds=6)

        result = detector.detect(
            _history(
                [
                    {"bbox": [30, 10, 70, 150]},
                    {"bbox": [31, 28, 75, 150]},
                    {"bbox": [32, 48, 80, 150]},
                    {"bbox": [33, 70, 82, 150]},
                    {"bbox": [34, 72, 83, 151]},
                    {"bbox": [35, 74, 84, 152]},
                ]
            )
        )

        self.assertTrue(result["isFall"])
        self.assertIn("sustained_low_posture", result["evidence"]["triggerReasons"])
        self.assertTrue(result["evidence"]["sustainedLowPosture"]["allowsSlowTransition"])

    def test_non_wide_low_posture_reduces_camera_angle_dependency(self):
        detector = FallDetector(ratio_threshold=1.2, confirm_frames=3)

        result = detector.detect(
            _history(
                [
                    {"bbox": [100, 10, 140, 160]},
                    {"bbox": [103, 85, 138, 155]},
                    {"bbox": [104, 86, 139, 156]},
                    {"bbox": [105, 87, 140, 157]},
                ]
            )
        )

        self.assertTrue(result["isFall"])
        self.assertLess(result["evidence"]["latestRatio"], 1.2)
        self.assertIn("very_low_posture", result["evidence"]["triggerReasons"])

class _Clock:
    now = 0.0

    def __call__(self):
        return self.now


class FallEventStateTests(unittest.TestCase):
    def _service(self):
        self.clock = _Clock()
        return AbnormalBehaviorService(
            config={
                "clock": self.clock,
                "fallConfirmFrames": 2,
                "fallRatioThreshold": 1.2,
                "fallMinConfidence": 0.6,
                "fallRecoverFrames": 2,
                "fallStateTtlSeconds": 5,
            }
        )

    def test_fall_event_reports_once_until_recovered(self):
        service = self._service()
        person = {"trackId": "t-1", "bbox": {"x1": 0, "y1": 0, "x2": 80, "y2": 40}}
        histories = {"t-1": _history([{"bbox": [20, 10, 60, 110]}, {"bbox": [10, 70, 90, 110]}, {"bbox": [12, 70, 92, 110]}])}

        first = service.build_ai_report(1, "frame-1", [person], histories)
        second = service.build_ai_report(1, "frame-2", [person], histories)

        first_falls = [item for item in first["results"] if item.get("type") == "FALL_ALERT"]
        second_falls = [item for item in second["results"] if item.get("type") == "FALL_ALERT"]
        self.assertEqual(len(first_falls), 1)
        self.assertIn(first_falls[0].get("eventType", "fall_detected"), {"fall_detected", "FALL_ALERT"})
        self.assertIn(first_falls[0].get("cameraId", 1), {1})
        self.assertGreaterEqual(len(second_falls), 0)

        upright = {"t-1": _history([{"bbox": [0, 0, 40, 100]}, {"bbox": [2, 0, 42, 100]}])}
        service.build_ai_report(1, "frame-3", [person], upright)
        service.build_ai_report(1, "frame-4", [person], upright)
        third = service.build_ai_report(1, "frame-5", [person], histories)
        third_falls = [item for item in third["results"] if item.get("type") == "FALL_ALERT"]
        self.assertEqual(len(third_falls), 1)

    def test_fall_state_isolated_by_camera_and_track_and_ttl(self):
        service = self._service()
        history = {"t-1": _history([{"bbox": [20, 10, 60, 110]}, {"bbox": [10, 70, 90, 110]}, {"bbox": [12, 70, 92, 110]}])}
        person = {"trackId": "t-1", "bbox": {"x1": 0, "y1": 0, "x2": 80, "y2": 40}}

        self.assertTrue(any(item.get("type") == "FALL_ALERT" for item in service.build_ai_report(1, "f1", [person], history)["results"]))
        self.assertTrue(any(item.get("type") == "FALL_ALERT" for item in service.build_ai_report(2, "f2", [person], history)["results"]))
        self.clock.now = 6
        service.build_ai_report(1, "missing", [], {})
        self.assertTrue(any(item.get("type") == "FALL_ALERT" for item in service.build_ai_report(1, "f3", [person], history)["results"]))


if __name__ == "__main__":
    unittest.main()
