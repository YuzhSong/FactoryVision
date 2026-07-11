import unittest

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
                    {"bbox": [0, 0, 80, 40]},
                    {"bbox": [2, 0, 82, 40]},
                ]
            )
        )

        self.assertTrue(result["isFall"])
        self.assertEqual(result["evidenceType"], "bbox")
        self.assertEqual(result["durationFrames"], 2)
        self.assertEqual(result["level"], "high")

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
                    {"bbox": [0, 0, 40, 100], "keypoints": _pose(40, 45)},
                    {"bbox": [2, 0, 42, 100], "keypoints": _pose(40, 45)},
                ]
            )
        )

        self.assertTrue(result["isFall"])
        self.assertEqual(result["evidenceType"], "pose")
        self.assertEqual(result["evidence"]["poseFrames"], 2)
        self.assertLessEqual(result["evidence"]["latestBodyAngle"], 35)

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


if __name__ == "__main__":
    unittest.main()
