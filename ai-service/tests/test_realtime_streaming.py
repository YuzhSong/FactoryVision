import unittest

from modules.frame_processor import FrameProcessor
from modules.processed_stream_service import LatestFrameSnapshot, ProcessedStreamService


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


class RealtimeStreamingTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
