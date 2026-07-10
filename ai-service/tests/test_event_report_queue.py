import threading
import time
import unittest

from modules.processed_stream_service import ProcessedStreamService


def _report(track_id="t-1", region_id="r-1", event_type="region_intrusion"):
    return {
        "cameraId": 1,
        "frameId": f"frame-{track_id}-{region_id}",
        "timestamp": "2026-07-11T10:00:00+08:00",
        "results": [{
            "type": "ZONE_WARNING",
            "eventType": event_type,
            "cameraId": 1,
            "trackId": track_id,
            "regionId": region_id,
            "enteredAt": "2026-07-11T10:00:00+08:00",
        }],
    }


class _Backend:
    def __init__(self, block=False, fail_first=False):
        self.items = []
        self.block = block
        self.fail_first = fail_first
        self.started = threading.Event()
        self.release = threading.Event()

    def report_ai_results(self, report):
        self.started.set()
        if self.block:
            self.release.wait(1)
        self.items.append(report)
        if self.fail_first:
            self.fail_first = False
            raise RuntimeError("expected test failure")


class EventReportQueueTests(unittest.TestCase):
    def _service(self, backend, size=8):
        return ProcessedStreamService(frame_processor=None, backend_client=backend, event_report_queue_size=size)

    def test_different_events_are_reported_fifo_without_overwrite(self):
        backend = _Backend(block=True)
        service = self._service(backend)
        for report in (_report("t-1", "r-1"), _report("t-2", "r-1"), _report("t-1", "r-2")):
            self.assertTrue(service._enqueue_ai_report(report))
        backend.release.set()
        service._shutdown_report_worker()
        self.assertEqual(
            [(item["results"][0]["trackId"], item["results"][0]["regionId"]) for item in backend.items],
            [("t-1", "r-1"), ("t-2", "r-1"), ("t-1", "r-2")],
        )
        self.assertEqual(service.status()["reported_events"], 3)

    def test_duplicate_continuous_stay_is_not_queued_twice(self):
        backend = _Backend(block=True)
        service = self._service(backend)
        self.assertTrue(service._enqueue_ai_report(_report()))
        self.assertFalse(service._enqueue_ai_report(_report()))
        backend.release.set()
        service._shutdown_report_worker()
        self.assertEqual(len(backend.items), 1)

    def test_failure_does_not_stop_worker(self):
        backend = _Backend(fail_first=True)
        service = self._service(backend)
        service._enqueue_ai_report(_report("t-1"))
        service._enqueue_ai_report(_report("t-2"))
        deadline = time.monotonic() + 1
        while len(backend.items) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        service._shutdown_report_worker()
        self.assertEqual(len(backend.items), 2)
        self.assertEqual(service.status()["failed_events"], 1)
        self.assertEqual(service.status()["reported_events"], 1)

    def test_full_queue_counts_drops_without_blocking(self):
        backend = _Backend(block=True)
        service = self._service(backend, size=1)
        service._enqueue_ai_report(_report("t-1"))
        self.assertTrue(backend.started.wait(1))
        service._enqueue_ai_report(_report("t-2"))
        started = time.monotonic()
        self.assertFalse(service._enqueue_ai_report(_report("t-3")))
        self.assertLess(time.monotonic() - started, 0.1)
        self.assertEqual(service.status()["dropped_events"], 1)
        backend.release.set()
        service._shutdown_report_worker()

    def test_shutdown_stops_the_single_worker(self):
        backend = _Backend()
        service = self._service(backend)
        service._enqueue_ai_report(_report())
        service._shutdown_report_worker()
        self.assertFalse(service._report_thread.is_alive())


if __name__ == "__main__":
    unittest.main()


def _region_event_keys(report):
    return {key for key in (_region_event_key(result) for result in report.get("results") or []) if key is not None}


def _region_event_key(result):
    if not isinstance(result, dict) or result.get("eventType") not in {"region_intrusion", "region_dwell"}:
        return None
    return (
        str(result.get("cameraId")),
        str(result.get("regionId")),
        str(result.get("trackId")),
        str(result.get("eventType")),
        str(result.get("enteredAt")),
    )
