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
        self.assertEqual(executed["helmet"], [2, 6, 11, 14, 18, 22, 26, 31, 34, 38, 42, 46, 51, 54, 58])
        self.assertEqual(executed["face"], [3, 32])
        service._status.processed_frames = 2
        self.assertFalse(service._model_runs(include_faces=False)["face"])

    def test_face_run_is_deferred_instead_of_dropped_when_due_frame_conflicts(self):
        service = ProcessedStreamService(frame_processor=None)
        executed = {"person": [], "helmet": [], "face": []}
        for frame in range(94):
            service._status.processed_frames = frame
            runs = service._model_runs(include_faces=True)
            for model, should_run in runs.items():
                if should_run:
                    executed[model].append(frame)
        self.assertIn(91, executed["helmet"])
        self.assertIn(92, executed["face"])
        self.assertEqual(executed["face"], [3, 32, 63, 92])


if __name__ == "__main__":
    unittest.main()
