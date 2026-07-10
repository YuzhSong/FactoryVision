from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cameras.models import Camera

from .models import Event


class EventListTests(TestCase):
    def test_list_returns_formal_events(self):
        camera = Camera.objects.create(name="Workshop A", code="CAM-A")
        event = Event.objects.create(
            camera=camera,
            camera_identifier=camera.code,
            event_type="PERSON_DETECTION",
            occurred_at=timezone.now(),
        )

        response = APIClient().get("/api/events/list/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total"], 1)
        self.assertEqual(response.data["data"]["items"][0]["id"], event.id)
        self.assertEqual(response.data["data"]["items"][0]["cameraIdentifier"], camera.code)
