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
        self.last_predict_kwargs = None

    def predict(self, **kwargs):
        self.last_predict_kwargs = kwargs
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


class _ManualClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


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
        self.assertEqual(detector.last_diagnostics["helmetCount"], 1)
        self.assertEqual(detector.last_diagnostics["noHelmetCount"], 1)
        self.assertEqual(detector.last_diagnostics["nmsBoxCount"], 2)
        self.assertEqual(detector.last_diagnostics["finalDrawCount"], 2)
        self.assertEqual(detector.last_diagnostics["rawCandidateSource"], "not_exposed_by_ultralytics_predict")

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
        self.assertEqual(detector.last_diagnostics["personCount"], 2)
        self.assertEqual(detector.last_diagnostics["matchedCount"], 1)
        self.assertEqual(detector.last_diagnostics["unmatchedHelmetCount"], 0)

    def test_predict_uses_configured_max_det_without_truncating_results(self):
        fake_model = _FakeModel(
            names={1: "helmet"},
            boxes=[
                _FakeBox(1, 0.9, [10, 10, 20, 20]),
                _FakeBox(1, 0.8, [30, 10, 40, 20]),
                _FakeBox(1, 0.7, [50, 10, 60, 20]),
            ],
        )
        detector = _HelmetDetectorForTest(
            fake_model,
            provider="self_trained",
            model_path="fake.pt",
            max_det=300,
            class_ids=(1, 2),
            helmet_class_id=1,
            no_helmet_class_id=2,
        )

        detections = detector.detect(frame=object(), frame_id="frame-many")

        self.assertEqual(len(detections), 3)
        self.assertEqual(fake_model.last_predict_kwargs["max_det"], 300)
        self.assertEqual(detector.last_diagnostics["finalDrawCount"], 3)

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

    def test_frame_processor_reuses_recent_helmet_box_between_detection_runs(self):
        clock = _ManualClock()
        processor = FrameProcessor(
            person_detector=_FakePersonDetector(),
            abnormal_config={"helmetModelPath": "", "helmetResultCacheTtlSeconds": 10, "clock": clock},
        )
        processor.abnormal_service.helmet_detector.detect = lambda *_args, **_kwargs: [
            {
                "type": "HELMET_DETECTION",
                "trackId": "t-1",
                "helmetStatus": "helmet",
                "helmetConfidence": 0.91,
                "bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45},
            }
        ]

        first = processor.process_frame(frame=object(), camera_id=1, frame_id="frame-1", include_faces=False)
        people = [item for item in first["results"] if item.get("type") == "PERSON_DETECTION"]
        clock.advance(2)

        second = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-2",
            include_faces=False,
            person_detections=people,
            run_person_detection=False,
            run_helmet_detection=False,
        )

        helmet_results = [item for item in second["results"] if item.get("type") == "HELMET_DETECTION"]
        self.assertEqual(len(helmet_results), 1)
        self.assertEqual(helmet_results[0]["helmetStatus"], "helmet")
        self.assertTrue(helmet_results[0]["cached"])

    def test_frame_processor_keeps_helmet_state_through_one_missing_person_frame(self):
        clock = _ManualClock()
        processor = FrameProcessor(
            person_detector=_FakePersonDetector(),
            abnormal_config={"helmetModelPath": "", "helmetResultCacheTtlSeconds": 5, "clock": clock},
        )
        processor.abnormal_service.helmet_detector.detect = lambda *_args, **_kwargs: [
            {
                "type": "HELMET_DETECTION",
                "trackId": "t-1",
                "helmetStatus": "helmet",
                "helmetConfidence": 0.91,
                "bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45},
            }
        ]

        processor.process_frame(frame=object(), camera_id=1, frame_id="frame-1", include_faces=False)
        clock.advance(1)
        processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-miss",
            include_faces=False,
            person_detections=[],
            run_person_detection=False,
            run_helmet_detection=False,
        )
        clock.advance(1)
        report = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-2",
            include_faces=False,
            person_detections=[{
                "type": "PERSON_DETECTION",
                "trackId": "t-1",
                "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210},
            }],
            run_person_detection=False,
            run_helmet_detection=False,
        )

        helmet_results = [item for item in report["results"] if item.get("type") == "HELMET_DETECTION"]
        self.assertEqual(len(helmet_results), 1)
        self.assertTrue(helmet_results[0]["cached"])

    def test_frame_processor_expires_helmet_state_after_ttl(self):
        clock = _ManualClock()
        processor = FrameProcessor(
            person_detector=_FakePersonDetector(),
            abnormal_config={"helmetModelPath": "", "helmetResultCacheTtlSeconds": 5, "clock": clock},
        )
        processor.abnormal_service.helmet_detector.detect = lambda *_args, **_kwargs: [
            {
                "type": "HELMET_DETECTION",
                "trackId": "t-1",
                "helmetStatus": "helmet",
                "helmetConfidence": 0.91,
                "bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45},
            }
        ]

        processor.process_frame(frame=object(), camera_id=1, frame_id="frame-1", include_faces=False)
        clock.advance(6)
        report = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-2",
            include_faces=False,
            person_detections=[{
                "type": "PERSON_DETECTION",
                "trackId": "t-1",
                "bbox": {"x1": 10, "y1": 10, "x2": 110, "y2": 210},
            }],
            run_person_detection=False,
            run_helmet_detection=False,
        )

        helmet_results = [item for item in report["results"] if item.get("type") == "HELMET_DETECTION"]
        self.assertEqual(helmet_results, [])

    def test_frame_processor_projects_cached_helmet_box_to_latest_person_box(self):
        clock = _ManualClock()
        processor = FrameProcessor(
            person_detector=_FakePersonDetector(),
            abnormal_config={"helmetModelPath": "", "helmetResultCacheTtlSeconds": 5, "clock": clock},
        )
        processor.abnormal_service.helmet_detector.detect = lambda *_args, **_kwargs: [
            {
                "type": "HELMET_DETECTION",
                "trackId": "t-1",
                "helmetStatus": "helmet",
                "helmetConfidence": 0.91,
                "bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45},
            }
        ]

        processor.process_frame(frame=object(), camera_id=1, frame_id="frame-1", include_faces=False)
        clock.advance(1)
        report = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-2",
            include_faces=False,
            person_detections=[{
                "type": "PERSON_DETECTION",
                "trackId": "t-1",
                "bbox": {"x1": 20, "y1": 20, "x2": 220, "y2": 420},
            }],
            run_person_detection=False,
            run_helmet_detection=False,
        )

        helmet = next(item for item in report["results"] if item.get("type") == "HELMET_DETECTION")
        self.assertEqual(helmet["bbox"], {"x1": 40.0, "y1": 40.0, "x2": 90.0, "y2": 90.0})

    def test_unmatched_helmet_detection_draws_once_without_persisting_to_person(self):
        clock = _ManualClock()
        processor = FrameProcessor(
            person_detector=_FakePersonDetector(),
            abnormal_config={"helmetModelPath": "", "helmetResultCacheTtlSeconds": 5, "clock": clock},
        )
        processor.abnormal_service.helmet_detector.detect = lambda *_args, **_kwargs: [
            {
                "type": "HELMET_DETECTION",
                "helmetStatus": "helmet",
                "helmetConfidence": 0.91,
                "bbox": {"x1": 20, "y1": 20, "x2": 45, "y2": 45},
            }
        ]

        first = processor.process_frame(frame=object(), camera_id=1, frame_id="frame-1", include_faces=False)
        first_helmets = [item for item in first["results"] if item.get("type") == "HELMET_DETECTION"]
        first_people = [item for item in first["results"] if item.get("type") == "PERSON_DETECTION"]
        self.assertEqual(len(first_helmets), 1)
        self.assertNotIn("helmetStatus", first_people[0])

        clock.advance(1)
        second = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-2",
            include_faces=False,
            person_detections=first_people,
            run_person_detection=False,
            run_helmet_detection=False,
        )
        second_helmets = [item for item in second["results"] if item.get("type") == "HELMET_DETECTION"]
        self.assertEqual(second_helmets, [])


if __name__ == "__main__":
    unittest.main()
