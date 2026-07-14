import unittest

from modules.frame_annotator import _color_for_result, _label_for_result


class FrameAnnotatorLabelTests(unittest.TestCase):
    def test_person_label_prefers_name_and_confidence(self):
        label = _label_for_result({
            "type": "PERSON_DETECTION",
            "trackId": "t-12",
            "name": "syz",
            "confidence": 0.901,
            "helmetStatus": "unknown",
        })

        self.assertEqual(label, "Person syz 0.90")
        self.assertNotIn("t-12", label)
        self.assertNotIn("Unknown", label)

    def test_person_label_falls_back_to_track_id(self):
        label = _label_for_result({
            "type": "PERSON_DETECTION",
            "trackId": "t-12",
            "confidence": 0.901,
            "helmetStatus": "unknown",
        })

        self.assertEqual(label, "Person t-12 0.90")

    def test_face_label_uses_name_and_confidence_only(self):
        label = _label_for_result({
            "type": "FACE_RESULT",
            "employeeId": 4,
            "employeeNo": "E004",
            "name": "张三",
            "similarity": 0.8234,
        })

        self.assertEqual(label, "张三 82.3%")
        self.assertNotIn("E004", label)
        self.assertNotIn("Emp", label)


    def test_person_box_stays_green_even_with_no_helmet_status(self):
        color = _color_for_result({
            "type": "PERSON_DETECTION",
            "helmetStatus": "no_helmet",
        })

        self.assertEqual(color, (0, 255, 0))

    def test_no_helmet_head_box_is_red(self):
        color = _color_for_result({
            "type": "HELMET_DETECTION",
            "helmetStatus": "no_helmet",
        })

        self.assertEqual(color, (0, 0, 255))


if __name__ == "__main__":
    unittest.main()
