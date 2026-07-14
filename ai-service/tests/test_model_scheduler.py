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

    def test_face_run_is_deferred_instead_of_dropped_when_due_frame_conflicts(self):
        service = ProcessedStreamService(frame_processor=None)
        executed = {"person": [], "helmet": [], "face": []}
        for frame in range(94):
            service._status.processed_frames = frame
            runs = service._model_runs(include_faces=True)
            for model, should_run in runs.items():
                if should_run:
                    executed[model].append(frame)
        self.assertIn(92, executed["helmet"])
        self.assertIn(93, executed["face"])
        self.assertEqual(executed["face"], [2, 32, 62, 93])

    def test_helmet_schedule_respects_runtime_switch(self):
        service = ProcessedStreamService(frame_processor=None)
        service._status.processed_frames = 4

        runs = service._model_runs(include_faces=True, include_helmet=False)

        self.assertEqual(runs, {"person": False, "helmet": False, "face": True})

    def test_helmet_waits_for_fresh_person_cache_in_live_service(self):
        service = ProcessedStreamService(frame_processor=object())
        service._status.processed_frames = 4

        runs = service._model_runs(include_faces=False, include_helmet=True)

        self.assertEqual(runs, {"person": False, "helmet": False, "face": False})
        self.assertTrue(service._helmet_waiting_for_fresh_people)

        service._status.processed_frames = 5
        self.assertEqual(service._model_runs(include_faces=False, include_helmet=True), {"person": True, "helmet": False, "face": False})
        service._person_cache_frame = 5
        service._status.processed_frames = 6

        self.assertEqual(service._model_runs(include_faces=False, include_helmet=True), {"person": False, "helmet": True, "face": False})


if __name__ == "__main__":
    unittest.main()
