import unittest

from modules.frame_annotator import _label_for_result


class FrameAnnotatorLabelTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
