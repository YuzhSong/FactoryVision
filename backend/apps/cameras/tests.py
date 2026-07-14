from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Camera


class CameraListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        Camera.objects.create(
            name="Workshop A",
            code="CAM-A",
            stream_url="rtmp://example/live/a",
            processed_stream_url="rtmp://example/live/a_ai",
            location="Line 1",
            status=Camera.Status.ONLINE,
            enabled=True,
        )

    def test_camera_list_returns_ai_service_fields(self):
        response = self.client.get("/api/cameras/list/")

        self.assertEqual(response.status_code, 200)
        item = response.data["data"]["items"][0]
        self.assertEqual(item["code"], "CAM-A")
        self.assertEqual(item["cameraId"], "CAM-A")
        self.assertEqual(item["streamUrl"], "rtmp://example/live/a")
        self.assertEqual(item["processedStreamUrl"], "rtmp://example/live/a_ai")
        self.assertTrue(item["enabled"])
        self.assertFalse(item["includeFaces"])
        self.assertEqual(item["streamConfig"]["cameraId"], item["id"])
        self.assertEqual(item["streamConfig"]["inputUrl"], item["streamUrl"])
        self.assertTrue(item["streamConfig"]["reportToBackend"])


class CameraStreamControlTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="stream-admin", password="test-pass-123")
        self.client.force_authenticate(self.user)
        self.camera = Camera.objects.create(
            name="Workshop A",
            code="CAM-A",
            stream_url="rtmp://81.70.90.222:1935/live/1",
            processed_stream_url="https://webrtc.rainycode.cn:8443/live/1_detected.flv",
            location="Line 1",
            status=Camera.Status.ONLINE,
            enabled=True,
            include_faces=True,
        )

    @patch("apps.cameras.views.requests.request")
    def test_camera_stream_start_uses_camera_runtime_config(self, request_mock):
        response_mock = MagicMock()
        response_mock.json.return_value = {"code": 200, "message": "success", "data": {"running": True}}
        response_mock.raise_for_status.return_value = None
        request_mock.return_value = response_mock

        response = self.client.post(f"/api/cameras/{self.camera.id}/stream/start/")

        self.assertEqual(response.status_code, 200)
        request_mock.assert_called_once()
        _, kwargs = request_mock.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertTrue(kwargs["url"].endswith("/streams/start"))
        self.assertEqual(
            kwargs["json"],
            {
                "configVersion": 1,
                "cameraId": self.camera.id,
                "inputUrl": "rtmp://81.70.90.222:1935/live/1",
                "outputUrl": "rtmp://81.70.90.222:1935/live/1_detected",
                "playUrl": "https://webrtc.rainycode.cn:8443/live/1_detected.flv",
                "includeFaces": True,
                "includeHelmet": True,
                "includeFall": True,
                "includeZone": True,
                "reportToBackend": True,
                "personDetectInterval": 5,
                "helmetDetectInterval": 8,
                "helmetDetectOffset": 4,
                "faceDetectInterval": 30,
                "faceDetectOffset": 2,
                "zoneRefreshIntervalSeconds": 10.0,
                "reconnectAttempts": 3,
                "reconnectDelaySeconds": 1.0,
                "zones": [],
            },
        )
        self.assertTrue(response.data["data"]["running"])

    @patch("apps.cameras.views.requests.request")
    def test_camera_stream_start_applies_detection_switch_overrides(self, request_mock):
        response_mock = MagicMock()
        response_mock.json.return_value = {"code": 200, "message": "success", "data": {"running": True}}
        response_mock.raise_for_status.return_value = None
        request_mock.return_value = response_mock

        response = self.client.post(
            f"/api/cameras/{self.camera.id}/stream/start/",
            {"includeFaces": False, "includeHelmet": False, "includeFall": False, "includeZone": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        _, kwargs = request_mock.call_args
        self.assertEqual(kwargs["json"]["includeFaces"], False)
        self.assertEqual(kwargs["json"]["includeHelmet"], False)
        self.assertEqual(kwargs["json"]["includeFall"], False)
        self.assertEqual(kwargs["json"]["includeZone"], False)

    @patch("apps.cameras.views.requests.request")
    def test_camera_stream_status_returns_current_ai_status(self, request_mock):
        response_mock = MagicMock()
        response_mock.json.return_value = {"code": 200, "message": "success", "data": {"running": False}}
        response_mock.raise_for_status.return_value = None
        request_mock.return_value = response_mock

        response = self.client.get(f"/api/cameras/{self.camera.id}/stream/status/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["data"]["running"])
        self.assertEqual(response.data["data"]["cameraConfig"]["cameraId"], self.camera.id)
