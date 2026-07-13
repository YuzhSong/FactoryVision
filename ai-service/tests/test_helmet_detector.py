import unittest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from modules.frame_processor import FrameProcessor
from modules.helmet_detector import HelmetDetector


class _FakeValue:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class _FakeArray:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return list(self.values)


class _FakeBox:
    def __init__(self, class_id, confidence, xyxy):
        self.cls = [_FakeValue(class_id)]
        self.conf = [_FakeValue(confidence)]
        self.xyxy = [_FakeArray(xyxy)]


class _FakePrediction:
    def __init__(self, boxes):
        self.boxes = boxes


class _FakeModel:
    def __init__(self, names, boxes):
        self.names = names
        self._boxes = boxes

    def predict(self, **_kwargs):
        return [_FakePrediction(self._boxes)]


class _FakePersonDetector:
    def detect(self, _frame, frame_id=None):
        return [
            {
                "type": "PERSON_DETECTION",
                "trackId": "t-1",
                "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210},
                "centerPoint": {"x": 60, "y": 110},
                "confidence": 0.9,
                "frameId": frame_id,
            }
        ]


class _HelmetDetectorForTest(HelmetDetector):
    def __init__(self, fake_model, **kwargs):
        super().__init__(**kwargs)
        self._fake_model = fake_model

    def load_model(self):
        self.model = self._fake_model
        self.class_names = dict(getattr(self.model, "names", {}) or {})
        self._refresh_class_id_cache()
        return self.model


class HelmetDetectorTests(unittest.TestCase):
    def test_opensource_provider_recognizes_helmet_and_no_helmet_by_class_name(self):
        detector = _HelmetDetectorForTest(
            _FakeModel(
                names={0: "helmet", 1: "no-hardhat"},
                boxes=[
                    _FakeBox(0, 0.91, [20, 20, 45, 45]),
                    _FakeBox(1, 0.88, [60, 20, 90, 45]),
                ],
            ),
            provider="opensource",
            model_path="fake.pt",
        )

        detections = detector.detect(frame=object(), frame_id="frame-1")

        self.assertEqual([item["helmetStatus"] for item in detections], ["helmet", "no_helmet"])

    def test_self_trained_provider_recognizes_helmet_and_no_helmet_by_class_id(self):
        detector = _HelmetDetectorForTest(
            _FakeModel(
                names={1: "anything", 2: "other"},
                boxes=[
                    _FakeBox(1, 0.91, [20, 20, 45, 45]),
                    _FakeBox(2, 0.88, [60, 20, 90, 45]),
                ],
            ),
            provider="self_trained",
            model_path="fake.pt",
            class_ids=(1, 2),
            helmet_class_id=1,
            no_helmet_class_id=2,
        )

        detections = detector.detect(frame=object(), frame_id="frame-1")

        self.assertEqual([item["helmetStatus"] for item in detections], ["helmet", "no_helmet"])

    def test_upper_body_matching_attaches_helmet_to_correct_person(self):
        detector = _HelmetDetectorForTest(
            _FakeModel(
                names={1: "helmet"},
                boxes=[_FakeBox(1, 0.9, [30, 20, 55, 50])],
            ),
            provider="self_trained",
            model_path="fake.pt",
            class_ids=(1, 2),
            helmet_class_id=1,
            no_helmet_class_id=2,
            match_upper_ratio=0.65,
        )
        persons = [
            {"trackId": "t-1", "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210}},
            {"trackId": "t-2", "bbox": {"x1": 200, "y1": 10, "x2": 300, "y2": 210}},
        ]

        detections = detector.detect(frame=object(), person_detections=persons, frame_id="frame-1")

        self.assertEqual(detections[0]["trackId"], "t-1")
        self.assertEqual(detections[0]["helmetStatus"], "helmet")

    def test_missing_helmet_detections_leave_person_status_unknown(self):
        detector = _HelmetDetectorForTest(
            _FakeModel(names={1: "helmet"}, boxes=[]),
            provider="opensource",
            model_path="fake.pt",
        )
        persons = [{"trackId": "t-1", "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210}}]

        helmet_results = detector.detect(frame=object(), person_detections=persons, frame_id="frame-1")
        detector.annotate_person_detections(persons, helmet_results)

        self.assertEqual(helmet_results, [])
        self.assertNotIn("helmetStatus", persons[0])

    def test_frame_processor_keeps_existing_helmet_detector_entrypoint(self):
        processor = FrameProcessor(
            person_detector=_FakePersonDetector(),
            abnormal_config={
                "helmetModelPath": "",
                "helmetModelProvider": "self_trained",
                "helmetClassIds": (1, 2),
                "helmetClassId": 1,
                "noHelmetClassId": 2,
            },
        )

        report = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-1",
            timestamp="2026-07-09T10:00:00+08:00",
            include_faces=False,
        )

        person_results = [item for item in report["results"] if item.get("type") == "PERSON_DETECTION"]
        self.assertEqual(len(person_results), 1)
        self.assertNotIn("helmetStatus", person_results[0])

    def test_frame_processor_keeps_helmet_boxes_for_stream_annotation(self):
        processor = FrameProcessor(person_detector=_FakePersonDetector(), abnormal_config={"helmetModelPath": ""})
        processor.abnormal_service.helmet_detector.detect = lambda *_args, **_kwargs: [
            {
                "type": "HELMET_DETECTION",
                "trackId": "t-1",
                "helmetStatus": "helmet",
                "helmetConfidence": 0.91,
                "bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45},
            }
        ]

        report = processor.process_frame(frame=object(), camera_id=1, frame_id="frame-1", include_faces=False)

        helmet_results = [item for item in report["results"] if item.get("type") == "HELMET_DETECTION"]
        self.assertEqual(len(helmet_results), 1)
        self.assertEqual(helmet_results[0]["helmetStatus"], "helmet")


if __name__ == "__main__":
    unittest.main()
