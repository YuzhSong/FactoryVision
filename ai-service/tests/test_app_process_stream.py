import unittest
from unittest.mock import patch

import app as app_module


class _FakeBackendClient:
    def __init__(self):
        self.report_payloads = []
        self.face_status = "not-called"

    def find_camera(self, camera_id):
        return {"id": int(camera_id), "streamUrl": "fake-stream-url"}

    def list_face_records(self, status="active"):
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
        return []

    def report_ai_results(self, payload):
        self.report_payloads.append(payload)
        return {"code": 200, "data": {"acceptedResults": len(payload.get("results", []))}}


class _FakeFaceService:
    def __init__(self):
        self.loaded_items = []

    def status(self):
        return {"loadedFaces": len(self.loaded_items), "modelLoaded": False}

    def load_face_library(self, employee_items=None, **_kwargs):
        self.loaded_items = employee_items or []
        return {"count": len(self.loaded_items), "errors": []}


class _FakeStreamReader:
    opened_url = None

    def __init__(self, *_args, **_kwargs):
        return None

    def open_stream(self, stream_url):
        type(self).opened_url = stream_url
        return self

    def iter_frames(self, max_frames=None, sample_interval=1):
        yield type(
            "Packet",
            (),
            {
                "frame": object(),
                "frame_id": "frame-000001",
                "timestamp": "2026-07-07T10:00:00+08:00",
                "frame_index": 1,
                "fps": 5,
            },
        )()

    def close_stream(self):
        return None


class _FakeFrameProcessor:
    def process_frame(self, _frame, **kwargs):
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
                }
            ],
        }


class ProcessStreamEndpointTests(unittest.TestCase):
    def test_process_stream_loads_camera_and_employee_faces_from_backend(self):
        fake_backend = _FakeBackendClient()
        fake_face_service = _FakeFaceService()

        with patch.object(app_module, "backend_client", fake_backend), patch.object(
            app_module, "face_service", fake_face_service
        ), patch.object(app_module, "StreamReader", _FakeStreamReader), patch.object(
            app_module, "frame_processor", _FakeFrameProcessor()
        ):
            response = app_module.app.test_client().post(
                "/process/stream",
                json={"cameraId": 1, "maxFrames": 1, "reportToBackend": True},
            )

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["streamUrl"], "fake-stream-url")
        self.assertEqual(payload["data"]["faceLibrary"]["count"], 1)
        self.assertEqual(fake_face_service.loaded_items[0]["employeeNo"], "E001")
        self.assertEqual(fake_backend.report_payloads[0]["cameraId"], 1)
        self.assertEqual(_FakeStreamReader.opened_url, "fake-stream-url")


if __name__ == "__main__":
    unittest.main()
