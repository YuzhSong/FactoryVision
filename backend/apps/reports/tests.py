from tempfile import TemporaryDirectory
from datetime import timedelta
from pathlib import Path
import zipfile

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai_results.models import Alert
from apps.cameras.models import Camera
from apps.events.models import Event

from .services import _alert_item, _write_word_document
from .views import _alert_keyframe_path


class ReportKeyframePathTests(TestCase):
    def test_report_prefers_uploaded_media_keyframe_over_stale_alert_snapshot(self):
        camera = Camera.objects.create(name="Workshop A", code="CAM-A")
        event = Event.objects.create(
            camera=camera,
            camera_identifier=camera.code,
            event_type="helmet_missing",
            occurred_at=timezone.now(),
            snapshot_path="events/1/keyframe.jpg",
            payload={
                "media": {
                    "keyframePath": "events/1/uploaded-keyframe.jpg",
                    "keyframeUrl": "/media/events/1/uploaded-keyframe.jpg",
                }
            },
        )
        alert = Alert.objects.create(
            event=event,
            camera=camera,
            event_type=event.event_type,
            level="medium",
            title="Helmet Missing",
            occurred_at=event.occurred_at,
            snapshot_path=r"D:\FactoryVision\event_media\stale-keyframe.jpg",
        )

        self.assertEqual(_alert_keyframe_path(alert), "events/1/uploaded-keyframe.jpg")
        self.assertEqual(_alert_item(alert)["keyframeUrl"], "/media/events/1/uploaded-keyframe.jpg")


class ReportWordDocumentTests(TestCase):
    def test_write_word_document_generates_valid_docx_with_chinese_text(self):
        now = timezone.now()
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root, MEDIA_URL="/media/"):
            document_path = _write_word_document(
                now,
                now + timedelta(hours=6),
                "00:00-06:00",
                "",
                [],
                "建议检查入口摄像头与安全帽佩戴情况。",
            )

            full_path = Path(media_root) / document_path
            self.assertTrue(zipfile.is_zipfile(full_path))
            with zipfile.ZipFile(full_path) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("FactoryVision AI 告警时段报告", document_xml)
            self.assertIn("建议检查入口摄像头与安全帽佩戴情况。", document_xml)
