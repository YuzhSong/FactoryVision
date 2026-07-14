from django.test import TestCase
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.utils import timezone
from django.test import override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from tempfile import TemporaryDirectory

from apps.cameras.models import Camera
from apps.ai_results.models import Alert

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

    def test_upload_event_media_updates_payload_with_urls(self):
        with TemporaryDirectory() as media_root:
            camera = Camera.objects.create(name="Workshop A", code="CAM-A")
            event = Event.objects.create(
                camera=camera,
                camera_identifier=camera.code,
                event_type="region_intrusion",
                occurred_at=timezone.now(),
                payload={"media": {"status": "recording"}},
            )
            alert = Alert.objects.create(
                event=event,
                camera=camera,
                event_type=event.event_type,
                level="medium",
                title="Region Intrusion",
                occurred_at=event.occurred_at,
                snapshot_path="event_media/cam-a/stale-keyframe.jpg",
            )

            with override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/"):
                response = APIClient().post(
                    f"/api/events/{event.id}/media/",
                    {
                        "mediaEventId": "local-media-1",
                        "status": "ready",
                        "keyframe": SimpleUploadedFile("keyframe.jpg", b"fake-image", content_type="image/jpeg"),
                        "clip": SimpleUploadedFile("clip.mp4", b"fake-video", content_type="video/mp4"),
                        "manifest": SimpleUploadedFile("manifest.json", b"{}", content_type="application/json"),
                    },
                    format="multipart",
                )

            self.assertEqual(response.status_code, 200)
            media = response.data["data"]
            self.assertEqual(media["mediaEventId"], "local-media-1")
            self.assertIn("/media/events/", media["keyframeUrl"])
            self.assertIn("/media/events/", media["clipUrl"])
            event.refresh_from_db()
            self.assertEqual(event.payload["media"]["status"], "ready")
            self.assertEqual(event.payload["media"]["keyframePath"], f"events/{event.id}/keyframe.jpg")
            self.assertEqual(event.snapshot_path, f"events/{event.id}/keyframe.jpg")
            alert.refresh_from_db()
            self.assertEqual(alert.snapshot_path, f"events/{event.id}/keyframe.jpg")


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
