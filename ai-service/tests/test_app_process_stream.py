import unittest
from unittest.mock import patch
import numpy as np

try:
    from fastapi.testclient import TestClient

    import app as app_module
except ModuleNotFoundError as exc:
    if exc.name == "fastapi":
        raise unittest.SkipTest("fastapi is not installed; run pip install -r requirements.txt")
    raise


class _FakeBackendClient:
    """Fake backend client for process-stream endpoint tests."""

    def __init__(self):
        """Initialize fake backend state."""
        self.report_payloads = []
        self.face_status = "not-called"

    def find_camera(self, camera_id):
        """Return one fake camera with streamUrl for camera_id."""
        return {"id": int(camera_id), "streamUrl": "fake-stream-url"}

    def list_face_records(self, status="active"):
        """Return one fake employee face record."""
        self.face_status = status
        return [
            {
                "id": 1,
                "employeeNo": "E001",
                "name": "Zhang San",
                "faceFeatures": [{"featureVector": [1.0, 0.0, 0.0]}],
            }
        ]

    def list_zones(self, camera_id):
        """Return no fake zones for camera_id."""
        return []

    def report_ai_results(self, payload):
        """Capture report payload and return fake backend response."""
        self.report_payloads.append(payload)
        return {"code": 200, "data": {"acceptedResults": len(payload.get("results", []))}}


class _FakeFaceService:
    """Fake face service that records loaded employee items."""

    def __init__(self):
        """Initialize empty fake face library."""
        self.loaded_items = []

    def status(self):
        """Return fake face-library status."""
        return {"loadedFaces": len(self.loaded_items), "modelLoaded": False}

    def load_face_library(self, employee_items=None, **_kwargs):
        """Store employee_items as fake loaded face library."""
        self.loaded_items = employee_items or []
        return {"count": len(self.loaded_items), "errors": []}


class _FakeStreamReader:
    """Fake stream reader that yields one frame packet."""

    opened_url = None

    def __init__(self, *_args, **_kwargs):
        """Initialize fake reader without external resources."""
        return None

    def open_stream(self, stream_url):
        """Capture opened stream_url and return self."""
        type(self).opened_url = stream_url
        return self

    def iter_frames(self, max_frames=None, sample_interval=1):
        """Yield one fake frame packet."""
        yield type(
            "Packet",
            (),
            {
                "frame": np.zeros((1280, 720, 3), dtype=np.uint8),
                "frame_id": "frame-000001",
                "timestamp": "2026-07-07T10:00:00+08:00",
                "frame_index": 1,
                "fps": 5,
            },
        )()

    def close_stream(self):
        """Close fake stream reader."""
        return None


class _FakeFrameProcessor:
    """Fake frame processor that returns a raw person box and an actionable alert."""

    def process_frame(self, _frame, **kwargs):
        """Return deterministic report for endpoint test."""
        return {
            "cameraId": kwargs["camera_id"],
            "frameId": kwargs["frame_id"],
            "timestamp": kwargs["timestamp"],
            "results": [
                {
                    "type": "PERSON_DETECTION",
                    "trackId": "t-1",
                    "bbox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
                    "confidence": 0.9,
                },
                {"type": "HELMET_WARNING", "trackId": "t-1", "confidence": 0.9},
            ],
        }


class ProcessStreamEndpointTests(unittest.TestCase):
    """Test /process/stream endpoint integration behavior."""

    def test_process_stream_loads_camera_and_employee_faces_from_backend(self):
        """Verify camera lookup, face loading, stream open, and filtered backend report."""
        fake_backend = _FakeBackendClient()
        fake_face_service = _FakeFaceService()

        with patch.object(app_module, "backend_client", fake_backend), patch.object(
            app_module, "face_service", fake_face_service
        ), patch.object(app_module, "StreamReader", _FakeStreamReader), patch.object(
            app_module, "frame_processor", _FakeFrameProcessor()
        ):
            response = TestClient(app_module.app).post(
                "/process/stream",
                json={"cameraId": 1, "maxFrames": 1, "reportToBackend": True},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["streamUrl"], "fake-stream-url")
        self.assertEqual(payload["data"]["faceLibrary"]["count"], 1)
        self.assertEqual(fake_face_service.loaded_items[0]["employeeNo"], "E001")
        self.assertEqual(fake_backend.report_payloads[0]["cameraId"], 1)
        self.assertEqual([item["type"] for item in fake_backend.report_payloads[0]["results"]], ["HELMET_WARNING"])
        self.assertEqual(_FakeStreamReader.opened_url, "fake-stream-url")

    def test_process_stream_rejects_removed_realtime_frame_reporting(self):
        response = TestClient(app_module.app).post(
            "/process/stream",
            json={"cameraId": 1, "reportRealtimeToBackend": True},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("no longer supported", response.json()["message"])


if __name__ == "__main__":
    unittest.main()
