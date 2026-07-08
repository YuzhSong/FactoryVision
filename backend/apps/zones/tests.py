from django.test import TestCase
from rest_framework.test import APIClient

from apps.cameras.models import Camera

from .models import Zone


class ZoneListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.camera = Camera.objects.create(name="Workshop A", code="CAM-A", status=Camera.Status.ONLINE)
        Zone.objects.create(
            camera=self.camera,
            name="Restricted Area",
            type=Zone.ZoneType.RESTRICTED,
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
            enabled=True,
            description="Robot arm area",
        )

    def test_zone_list_filters_by_camera_id(self):
        response = self.client.get(f"/api/zones/list/?cameraId={self.camera.id}")

        self.assertEqual(response.status_code, 200)
        item = response.data["data"]["items"][0]
        self.assertEqual(item["name"], "Restricted Area")
        self.assertEqual(item["cameraId"], self.camera.id)
        self.assertEqual(item["polygon"], item["points"])
