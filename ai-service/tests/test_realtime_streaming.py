import unittest
import time
import numpy as np

from modules.frame_processor import FrameProcessor
from modules.processed_stream_service import LatestFrameSnapshot, ProcessedStreamService, normalize_camera_frame


class _FakeDetector:
    def __init__(self):
        self.index = 0

    def detect(self, _frame, frame_id=None):
        self.index += 1
        x1 = float(self.index)
        return [
            {
                "type": "PERSON_DETECTION",
                "trackId": "t-1",
                "bbox": {"x1": x1, "y1": 2.0, "x2": x1 + 10.0, "y2": 42.0},
                "centerPoint": {"x": x1 + 5.0, "y": 22.0},
                "confidence": 0.9,
                "frameId": frame_id,
            }
        ]


class _FakeFaceService:
    def __init__(self, loaded_faces=1):
        self.loaded_faces = loaded_faces

    def status(self):
        return {"loadedFaces": self.loaded_faces}

    def recognize(self, _frame, person_detections=None, frame_id=None):
        return [
            {
                "type": "FACE_RESULT",
                "trackId": "t-1",
                "matched": False,
                "label": "unknown",
                "similarity": 0.2,
                "threshold": 0.45,
                "faceBox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
                "frameId": frame_id,
            }
        ]


class _SequencedFaceService:
    def __init__(self, results_by_call, loaded_faces=1):
        self.results_by_call = results_by_call
        self.loaded_faces = loaded_faces
        self.index = 0

    def status(self):
        return {"loadedFaces": self.loaded_faces}

    def recognize(self, _frame, person_detections=None, frame_id=None):
        results = self.results_by_call[min(self.index, len(self.results_by_call) - 1)]
        self.index += 1
        return [dict(result, frameId=frame_id) for result in results]


class _FakeAlertFrameProcessor:
    def process_frame(self, _frame, **kwargs):
        return {
            "cameraId": kwargs.get("camera_id"),
            "frameId": kwargs.get("frame_id"),
            "timestamp": kwargs.get("timestamp"),
            "results": [{"type": "HELMET_WARNING", "trackId": "t-1", "helmetStatus": "no_helmet"}],
        }


class _FakeAnnotator:
    def draw_results(self, frame, _results):
        return frame

    def draw_test_box(self, frame, frame_id=None):
        return frame

    def draw_debug_overlay(self, frame, _metrics):
        return frame


class _FakeEventMediaRecorder:
    def __init__(self):
        self.calls = []

    def record_frame(self, frame, frame_id=None, timestamp=None, report=None):
        self.calls.append({"frame": frame, "frameId": frame_id, "timestamp": timestamp, "report": report})
        if report and report.get("results"):
            return [{"eventId": "event-1", "keyframePath": "keyframe.jpg", "clipPath": "clip.mp4"}]
        return []

    def reset(self):
        self.calls.clear()

    def flush(self):
        return None


class _FakeBackendClient:
    def __init__(self):
        self.report = None

    def report_ai_results(self, payload):
        self.report = payload
        return {"code": 200}


class _FakePoseDetector(_FakeDetector):
    def detect(self, _frame, frame_id=None):
        detection = super().detect(_frame, frame_id=frame_id)[0]
        detection["keypoints"] = [[0, 0, 0.0] for _ in range(17)]
        detection["keypoints"][5] = [10, 40, 0.9]
        detection["keypoints"][6] = [30, 40, 0.9]
        detection["keypoints"][11] = [60, 45, 0.9]
        detection["keypoints"][12] = [80, 45, 0.9]
        return [detection]


class RealtimeStreamingTests(unittest.TestCase):
    def test_normalize_camera_frame_rotates_counterclockwise(self):
        base = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
        frame = np.dstack([base, base, base])

        rotated = normalize_camera_frame(frame)

        self.assertEqual(rotated.shape[:2], (3, 2))
        self.assertTrue(
            np.array_equal(
                rotated[:, :, 0],
                np.array([[3, 6], [2, 5], [1, 4]], dtype=np.uint8),
            )
        )

    def test_prepare_packet_rotates_before_resize_and_keeps_landscape_output(self):
        service = ProcessedStreamService(frame_processor=None, input_width=640, input_height=360)
        packet = type("Packet", (), {"frame": np.zeros((1280, 720, 3), dtype=np.uint8)})()

        prepared = service._prepare_packet(packet)

        self.assertEqual(prepared.frame.shape[:2], (360, 640))
        self.assertEqual(service.status()["input_frame_shape"], [1280, 720])
        self.assertEqual(service.status()["normalized_frame_shape"], [720, 1280])
        self.assertEqual(service.status()["output_frame_size"], [640, 360])

    def test_latest_frame_publish_drops_unprocessed_frames(self):
        service = ProcessedStreamService(frame_processor=None)

        first = type("Packet", (), {"frame_id": "frame-1"})()
        second = type("Packet", (), {"frame_id": "frame-2"})()
        third = type("Packet", (), {"frame_id": "frame-3"})()

        service._publish_latest_frame(first)
        service._publish_latest_frame(second)
        service._publish_latest_frame(third)

        self.assertEqual(service.status()["dropped_frames"], 2)

        snapshot = LatestFrameSnapshot(packet=third, sequence=3, captured_at=0)
        service._mark_processed(snapshot, process_time_ms=1.2, frame_age_ms=3.4)

        fourth = type("Packet", (), {"frame_id": "frame-4"})()
        service._publish_latest_frame(fourth)

        self.assertEqual(service.status()["dropped_frames"], 2)

    def test_detect_interval_skips_intermediate_frames(self):
        service = ProcessedStreamService(frame_processor=None, detect_interval=5)

        self.assertTrue(service._should_detect())
        service._status.processed_frames = 1
        self.assertFalse(service._should_detect())
        service._status.processed_frames = 4
        self.assertFalse(service._should_detect())
        service._status.processed_frames = 5
        self.assertTrue(service._should_detect())

    def test_model_schedule_offsets_person_helmet_and_face_work(self):
        service = ProcessedStreamService(
            frame_processor=None,
            person_detect_interval=10,
            helmet_detect_interval=10,
            helmet_detect_offset=5,
            face_detect_interval=60,
            face_detect_offset=2,
        )

        self.assertEqual(service._model_runs(include_faces=False), {"person": True, "helmet": False, "face": False})
        service._status.processed_frames = 2
        self.assertEqual(service._model_runs(include_faces=True), {"person": False, "helmet": False, "face": True})
        service._status.processed_frames = 5
        self.assertEqual(service._model_runs(include_faces=True), {"person": False, "helmet": True, "face": False})
        service._status.processed_frames = 10
        self.assertEqual(service._model_runs(include_faces=True), {"person": True, "helmet": False, "face": False})

    def test_frame_processor_uses_cached_people_for_offset_helmet_detection(self):
        processor = FrameProcessor(person_detector=_FakeDetector(), history_limit=5)
        helmet_detector = processor.abnormal_service.helmet_detector
        calls = []

        def fake_helmet_detect(_frame, person_detections=None, frame_id=None, **_kwargs):
            calls.append(list(person_detections or []))
            return [
                {
                    "type": "HELMET_DETECTION",
                    "trackId": "t-1",
                    "helmetStatus": "helmet",
                    "helmetConfidence": 0.9,
                    "className": "helmet",
                    "bbox": {"x1": 1, "y1": 2, "x2": 8, "y2": 9},
                    "frameId": frame_id,
                }
            ]

        helmet_detector.detect = fake_helmet_detect
        first = processor.process_frame(frame=object(), include_faces=False, run_helmet_detection=False)
        cached_people = [item for item in first["results"] if item.get("type") == "PERSON_DETECTION"]
        report = processor.process_frame(
            frame=object(),
            include_faces=False,
            person_detections=cached_people,
            run_person_detection=False,
            run_helmet_detection=True,
        )

        self.assertEqual(calls[0][0]["trackId"], "t-1")
        person = next(item for item in report["results"] if item.get("type") == "PERSON_DETECTION")
        self.assertEqual(person["helmetStatus"], "helmet")
        self.assertIn("helmet", report["modelTimingsMs"])

    def test_processed_stream_attaches_event_media_before_backend_report(self):
        backend = _FakeBackendClient()
        recorder = _FakeEventMediaRecorder()
        service = ProcessedStreamService(
            frame_processor=_FakeAlertFrameProcessor(),
            backend_client=backend,
            annotator=_FakeAnnotator(),
            event_media_recorder=recorder,
            detect_interval=1,
        )
        service._status.camera_id = 1
        packet = type(
            "Packet",
            (),
            {
                "frame": object(),
                "frame_id": "frame-alert",
                "frame_index": 1,
                "timestamp": "2026-07-08T03:00:00+08:00",
                "fps": 10,
            },
        )()
        snapshot = LatestFrameSnapshot(packet=packet, sequence=1, captured_at=0)

        service._process_snapshot(
            snapshot=snapshot,
            writer=None,
            include_faces=True,
            report_to_backend=True,
            zones=None,
            last_report={"results": []},
        )

        deadline = time.monotonic() + 1
        while backend.report is None and time.monotonic() < deadline:
            time.sleep(0.01)

        self.assertEqual(service.status()["event_media_count"], 1)
        self.assertEqual(backend.report["eventMedia"][0]["eventId"], "event-1")
        self.assertEqual(recorder.calls[0]["report"]["results"][0]["type"], "HELMET_WARNING")

    def test_live_stream_reports_only_actionable_results(self):
        service = ProcessedStreamService(frame_processor=None)
        report = {
            "cameraId": 1,
            "results": [
                {"type": "PERSON_DETECTION", "trackId": "person-1"},
                {"type": "PERSON_DETECTION", "eventType": "face_recognized", "trackId": "person-spoof"},
                {"type": "HELMET_DETECTION", "trackId": "person-1"},
                {"type": "HELMET_WARNING", "trackId": "person-1"},
                {"type": "FACE_RESULT", "trackId": "person-1", "matched": False},
                {"type": "FACE_RESULT", "trackId": "person-2", "matched": True, "employeeId": 4},
                {"type": "FACE_RECOGNIZED", "trackId": "person-2", "employeeId": 4},
                {"type": "ZONE_WARNING", "trackId": "person-1"},
            ],
        }

        filtered = service._reportable_event_report(report)

        self.assertEqual(
            [item["type"] for item in filtered["results"]],
            ["HELMET_WARNING", "FACE_RECOGNIZED", "ZONE_WARNING"],
        )
        self.assertEqual(service.status()["filtered_results"], 5)

    def test_reporting_requires_camera_id_and_rejects_legacy_realtime_path(self):
        service = ProcessedStreamService(frame_processor=None, default_report_to_backend=True)
        with self.assertRaisesRegex(ValueError, "cameraId"):
            service.start({})
        with self.assertRaisesRegex(ValueError, "reportRealtimeToBackend"):
            service.start({"reportRealtimeToBackend": True})

    def test_track_history_keeps_lightweight_recent_points(self):
        processor = FrameProcessor(person_detector=_FakeDetector(), history_limit=5)

        for index in range(7):
            processor.process_frame(
                frame=object(),
                frame_id=f"frame-{index}",
                timestamp=f"2026-07-08T03:00:0{index}+08:00",
                include_faces=False,
                frame_index=index,
                fps=10,
            )

        history = processor.track_histories["t-1"]
        self.assertEqual(len(history), 5)
        self.assertEqual(set(history[-1]).issuperset({"trackId", "timestamp", "center", "bbox"}), True)
        self.assertIsInstance(history[-1]["center"], list)
        self.assertIsInstance(history[-1]["bbox"], list)
        self.assertNotIn("frame", history[-1])
        self.assertIn("speed", history[-1])

    def test_track_history_keeps_pose_keypoints_when_available(self):
        processor = FrameProcessor(person_detector=_FakePoseDetector(), history_limit=5)

        processor.process_frame(
            frame=object(),
            frame_id="frame-pose",
            timestamp="2026-07-08T03:00:00+08:00",
            include_faces=False,
            frame_index=1,
            fps=10,
        )

        history = processor.track_histories["t-1"]
        self.assertIn("keypoints", history[-1])
        self.assertEqual(len(history[-1]["keypoints"]), 17)

    def test_frame_processor_confirms_stranger_after_multiple_unknown_frames(self):
        processor = FrameProcessor(
            person_detector=_FakeDetector(),
            face_service=_FakeFaceService(),
            abnormal_config={
                "strangerConfirmFrames": 3,
                "strangerCooldownSeconds": 30,
                "strangerMatchDistanceThreshold": 80,
            },
        )

        reports = [
            processor.process_frame(
                frame=object(),
                camera_id=1,
                frame_id=f"frame-{index}",
                timestamp=f"2026-07-08T03:00:0{index}+08:00",
                include_faces=True,
                frame_index=index,
                fps=10,
            )
            for index in range(3)
        ]

        self.assertFalse(any(result.get("type") == "STRANGER_ALERT" for result in reports[0]["results"]))
        self.assertFalse(any(result.get("type") == "STRANGER_ALERT" for result in reports[1]["results"]))
        self.assertTrue(any(result.get("type") == "STRANGER_ALERT" for result in reports[2]["results"]))

    def test_frame_processor_does_not_confirm_stranger_without_loaded_face_library(self):
        processor = FrameProcessor(
            person_detector=_FakeDetector(),
            face_service=_FakeFaceService(loaded_faces=0),
            abnormal_config={"strangerConfirmFrames": 1},
        )

        report = processor.process_frame(
            frame=object(),
            camera_id=1,
            frame_id="frame-no-library",
            timestamp="2026-07-08T03:00:00+08:00",
            include_faces=True,
            frame_index=1,
            fps=10,
        )

        self.assertFalse(any(result.get("type") == "STRANGER_ALERT" for result in report["results"]))

    def test_frame_processor_emits_leave_and_return_presence_events(self):
        recognized = {
            "type": "FACE_RESULT",
            "trackId": "t-1",
            "matched": True,
            "employeeId": 1,
            "employeeNo": "E001",
            "name": "Zhang San",
            "similarity": 0.9,
            "faceBox": {"x1": 10, "y1": 10, "x2": 50, "y2": 50},
        }
        processor = FrameProcessor(
            person_detector=_FakeDetector(),
            face_service=_SequencedFaceService([[recognized], [], [recognized]]),
            abnormal_config={"employeeAbsenceTimeoutSeconds": 5},
        )

        reports = [
            processor.process_frame(
                frame=object(),
                camera_id=1,
                frame_id=f"frame-{index}",
                timestamp=timestamp,
                include_faces=True,
                frame_index=index,
                fps=10,
            )
            for index, timestamp in enumerate(
                [
                    "2026-07-08T03:00:00+08:00",
                    "2026-07-08T03:00:06+08:00",
                    "2026-07-08T03:00:10+08:00",
                ]
            )
        ]

        leave_events = [
            result
            for result in reports[1]["results"]
            if result.get("type") == "EMPLOYEE_PRESENCE_EVENT"
        ]
        return_events = [
            result
            for result in reports[2]["results"]
            if result.get("type") == "EMPLOYEE_PRESENCE_EVENT"
        ]

        self.assertEqual(leave_events[0]["eventType"], "LEAVE")
        self.assertEqual(leave_events[0]["employeeId"], 1)
        self.assertEqual(return_events[0]["eventType"], "RETURN")
        self.assertEqual(return_events[0]["leaveDurationSeconds"], 10.0)


if __name__ == "__main__":
    unittest.main()
