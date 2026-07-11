from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai_results.models import Alert
from apps.cameras.models import Camera
from apps.employees.models import Employee
from apps.events.models import Event
from apps.zones.models import Zone


class AIResultsReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.camera = Camera.objects.create(
            name="Workshop A",
            code="CAM-A",
            stream_url="rtmp://example/live/a",
            processed_stream_url="rtmp://example/live/a_ai",
            status=Camera.Status.ONLINE,
        )

    def test_report_endpoint_accepts_valid_payload(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": self.camera.id,
                "frameId": "frame-0001",
                "timestamp": "2026-07-07T10:00:00+08:00",
                "results": [
                    {
                        "type": "PERSON_DETECTION",
                        "trackId": "t-1",
                        "bbox": {"x1": 10, "y1": 20, "x2": 30, "y2": 40},
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["message"], "AI results accepted")
        self.assertEqual(response.data["data"]["acceptedResults"], 1)
        self.assertEqual(response.data["data"]["rejectedResults"], 0)
        self.assertEqual(str(response.data["data"]["cameraId"]), str(self.camera.id))
        self.assertEqual(response.data["data"]["frameId"], "frame-0001")
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Alert.objects.count(), 0)
        event = Event.objects.get()
        self.assertEqual(response.data["data"]["eventIds"], [event.id])
        self.assertEqual(event.event_type, "PERSON_DETECTION")
        self.assertEqual(event.severity, Event.Severity.INFO)
        self.assertEqual(event.track_id, "t-1")

    def test_report_endpoint_persists_helmet_warning_event_and_alert(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": self.camera.code,
                "frameId": "frame-0002",
                "timestamp": "2026-07-07T10:01:00+08:00",
                "results": [
                    {
                        "type": "HELMET_WARNING",
                        "trackId": "t-1",
                        "level": "high",
                        "confidence": 0.91,
                        "bbox": {"x1": 10, "y1": 20, "x2": 30, "y2": 40},
                        "snapshotPath": "events/cam-a/frame-0002.jpg",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["acceptedResults"], 1)
        self.assertEqual(response.data["data"]["rejectedResults"], 0)
        self.assertEqual(len(response.data["data"]["eventIds"]), 1)
        self.assertEqual(len(response.data["data"]["alertIds"]), 1)

        event = Event.objects.get()
        alert = Alert.objects.get()
        self.assertEqual(event.camera, self.camera)
        self.assertEqual(event.event_type, "HELMET_WARNING")
        self.assertEqual(event.confidence, 0.91)
        self.assertEqual(event.snapshot_path, "events/cam-a/frame-0002.jpg")
        self.assertEqual(event.severity, "high")
        self.assertEqual(alert.event, event)
        self.assertEqual(alert.level, "high")
        self.assertEqual(alert.status, Alert.Status.PENDING)

    def test_report_endpoint_persists_fall_alert_event_and_alert(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": self.camera.id,
                "frameId": "frame-fall-0001",
                "timestamp": "2026-07-07T10:02:00+08:00",
                "results": [
                    {
                        "type": "FALL_ALERT",
                        "trackId": "t-9",
                        "isFall": True,
                        "confidence": 0.86,
                        "durationFrames": 5,
                        "evidenceType": "pose",
                        "level": "high",
                        "bbox": {"x1": 100, "y1": 120, "x2": 260, "y2": 220},
                        "snapshotPath": "events/cam-a/fall.jpg",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "AI results accepted")
        self.assertEqual(response.data["data"]["acceptedResults"], 1)
        self.assertEqual(response.data["data"]["rejectedResults"], 0)
        self.assertEqual(len(response.data["data"]["eventIds"]), 1)
        self.assertEqual(len(response.data["data"]["alertIds"]), 1)

        event = Event.objects.get()
        alert = Alert.objects.get()
        self.assertEqual(event.event_type, "FALL_ALERT")
        self.assertEqual(event.severity, Event.Severity.HIGH)
        self.assertEqual(event.track_id, "t-9")
        self.assertEqual(event.confidence, 0.86)
        self.assertEqual(event.snapshot_path, "events/cam-a/fall.jpg")
        self.assertTrue(event.payload["isFall"])
        self.assertEqual(alert.event, event)
        self.assertEqual(alert.event_type, "FALL_ALERT")
        self.assertEqual(alert.level, "high")
        self.assertEqual(alert.status, Alert.Status.PENDING)

    def test_report_endpoint_rejects_invalid_payload(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": 0,
                "frameId": "",
                "results": {},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)
        self.assertEqual(response.data["message"], "Invalid AI report payload")
        self.assertIn("timestamp", response.data["data"])
        self.assertIn("results", response.data["data"])


class AIBootstrapTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.camera = Camera.objects.create(
            name="Workshop A",
            code="CAM-A",
            stream_url="rtmp://example/live/a",
            status=Camera.Status.ONLINE,
        )
        Zone.objects.create(
            camera=self.camera,
            name="Restricted Area",
            points=[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
        )
        Employee.objects.create(employee_no="E001", name="Alice", status=Employee.Status.ACTIVE)

    def test_bootstrap_returns_cameras_zones_employees_and_thresholds(self):
        response = self.client.get("/api/ai/bootstrap/")

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["cameras"][0]["code"], "CAM-A")
        self.assertEqual(data["zones"][0]["cameraId"], self.camera.id)
        self.assertEqual(data["employees"][0]["employeeNo"], "E001")
        self.assertIn("helmet", data["thresholds"])
        self.assertIn("timestamp", data)


class AlertApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.camera = Camera.objects.create(name="Workshop A", code="CAM-A", status=Camera.Status.ONLINE)
        self.other_camera = Camera.objects.create(name="Workshop B", code="CAM-B", status=Camera.Status.OFFLINE)
        self.high_alert = self._create_alert(self.camera, "ZONE_WARNING", "high", Alert.Status.PENDING)
        self.medium_alert = self._create_alert(self.other_camera, "HELMET_WARNING", "medium", Alert.Status.PROCESSING)
        self._create_alert(self.camera, "FALL_ALERT", "high", Alert.Status.CLOSED)

    def _create_alert(self, camera, event_type, level, status):
        event = Event.objects.create(
            camera=camera,
            camera_identifier=camera.code,
            event_type=event_type,
            severity=level,
            occurred_at=timezone.now(),
        )
        return Alert.objects.create(
            event=event,
            camera=camera,
            event_type=event_type,
            level=level,
            status=status,
            title=event_type.replace("_", " ").title(),
            description="Test alert",
            occurred_at=event.occurred_at,
        )

    def test_alert_list_returns_paginated_serialized_alerts(self):
        response = self.client.get("/api/alerts/list/?page=1&pageSize=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total"], 3)
        self.assertEqual(len(response.data["data"]["items"]), 2)
        item = response.data["data"]["items"][0]
        self.assertEqual(
            set(item),
            {"id", "title", "eventType", "severity", "status", "cameraId", "cameraName", "occurredAt", "description"},
        )

    def test_alert_list_filters_by_severity_status_and_camera(self):
        response = self.client.get(
            f"/api/alerts/list/?severity=high&status=pending&cameraId={self.camera.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total"], 1)
        self.assertEqual(response.data["data"]["items"][0]["id"], self.high_alert.id)

    def test_handle_alert_updates_status(self):
        response = self.client.post(
            f"/api/alerts/{self.high_alert.id}/handle/",
            {"status": Alert.Status.CLOSED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.high_alert.refresh_from_db()
        self.assertEqual(self.high_alert.status, Alert.Status.CLOSED)
        self.assertEqual(response.data["data"]["status"], Alert.Status.CLOSED)


class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.online_camera = Camera.objects.create(name="Online", code="CAM-ONLINE", status=Camera.Status.ONLINE)
        Camera.objects.create(name="Offline", code="CAM-OFFLINE", status=Camera.Status.OFFLINE)
        Employee.objects.create(employee_no="EMP-001", name="Alice")
        Employee.objects.create(employee_no="EMP-002", name="Bob")
        now = timezone.now()
        self.today_event = Event.objects.create(
            camera=self.online_camera,
            camera_identifier=self.online_camera.code,
            event_type="ZONE_WARNING",
            severity=Event.Severity.HIGH,
            occurred_at=now,
        )
        Event.objects.create(
            camera=self.online_camera,
            camera_identifier=self.online_camera.code,
            event_type="PERSON_DETECTION",
            occurred_at=now,
        )
        Event.objects.create(
            camera=self.online_camera,
            camera_identifier=self.online_camera.code,
            event_type="OLD_EVENT",
            occurred_at=now - timedelta(days=1),
        )
        Alert.objects.create(
            event=self.today_event,
            camera=self.online_camera,
            event_type="ZONE_WARNING",
            level="high",
            status=Alert.Status.PENDING,
            title="Zone warning",
            occurred_at=now,
        )

    def test_dashboard_summary_returns_database_counts_and_trend(self):
        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["cameraCount"], 2)
        self.assertEqual(data["onlineCameraCount"], 1)
        self.assertEqual(data["employeeCount"], 2)
        self.assertEqual(data["todayEventCount"], 2)
        self.assertEqual(data["todayAlertCount"], 1)
        self.assertEqual(data["pendingAlertCount"], 1)
        self.assertEqual(len(data["recentAlerts"]), 1)
        self.assertEqual(sum(item["count"] for item in data["eventTrend"]), 2)
