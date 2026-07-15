import unittest

from modules.person_detector import PersonDetector


def _box(x1, y1, x2, y2, confidence=0.9):
    return (x1, y1, x2, y2, confidence)


class PersonDetectorTrackingTests(unittest.TestCase):
    def setUp(self):
        self.detector = PersonDetector(model_path="unused.pt", track_iou_threshold=0.3)

    def test_upright_to_horizontal_transition_keeps_track_id(self):
        upright = self.detector._assign_tracks([_box(100, 20, 160, 220)])
        fallen = self.detector._assign_tracks([_box(80, 160, 260, 230)])

        self.assertEqual(upright[0][0], "t-1")
        self.assertEqual(fallen[0][0], "t-1")

    def test_far_horizontal_person_does_not_reuse_upright_track(self):
        self.detector._assign_tracks([_box(100, 20, 160, 220)])
        fallen = self.detector._assign_tracks([_box(400, 160, 580, 230)])

        self.assertEqual(fallen[0][0], "t-2")

    def test_iou_matches_are_resolved_before_fall_transition_fallback(self):
        first = self.detector._assign_tracks(
            [_box(100, 20, 160, 220), _box(300, 20, 360, 220)]
        )
        second = self.detector._assign_tracks(
            [_box(80, 160, 260, 230), _box(302, 22, 362, 222)]
        )

        self.assertEqual([item[0] for item in first], ["t-1", "t-2"])
        self.assertEqual([item[0] for item in second], ["t-1", "t-2"])


if __name__ == "__main__":
    unittest.main()
