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
