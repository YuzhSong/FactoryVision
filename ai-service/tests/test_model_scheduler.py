import unittest

from modules.processed_stream_service import ProcessedStreamService


class ModelSchedulerTests(unittest.TestCase):
    def test_default_schedule_executes_expected_frames_without_overlap(self):
        service = ProcessedStreamService(frame_processor=None)
        executed = {"person": [], "helmet": [], "face": []}
        for frame in range(61):
            service._status.processed_frames = frame
            runs = service._model_runs(include_faces=True)
            self.assertLessEqual(sum(runs.values()), 1)
            for model, should_run in runs.items():
                if should_run:
                    executed[model].append(frame)
        self.assertEqual(executed["person"], list(range(0, 61, 5)))
        self.assertEqual(executed["helmet"], [4, 12, 21, 28, 36, 44, 52])
        self.assertEqual(executed["face"], [2, 32])
        service._status.processed_frames = 2
        self.assertFalse(service._model_runs(include_faces=False)["face"])


if __name__ == "__main__":
    unittest.main()
