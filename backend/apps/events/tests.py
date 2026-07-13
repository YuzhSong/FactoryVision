from django.test import TestCase
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cameras.models import Camera

from .models import Event
from .consumers import RealtimeEventConsumer
from config.asgi import application


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


class RealtimeEventConsumerTests(TestCase):
    def test_camera_group_delivers_canonical_event_without_polling(self):
        async def scenario():
            communicator = WebsocketCommunicator(application, "/ws/realtime/1/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            payload = {
                "type": "EVENT_CREATED",
                "cameraId": 1,
                "payload": {"eventId": 99, "eventType": "face_recognized", "trackId": "t-1"},
            }
            await RealtimeEventConsumer.push_event(get_channel_layer(), 1, payload)
            received = await communicator.receive_json_from(timeout=1)
            await communicator.disconnect()
            self.assertEqual(received, payload)

        async_to_sync(scenario)()
