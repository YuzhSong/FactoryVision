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

    def test_report_endpoint_rejects_non_actionable_detection(self):
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
        self.assertEqual(response.data["data"]["acceptedResults"], 0)
        self.assertEqual(response.data["data"]["rejectedResults"], 1)
        self.assertEqual(str(response.data["data"]["cameraId"]), str(self.camera.id))
        self.assertEqual(response.data["data"]["frameId"], "frame-0001")
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Alert.objects.count(), 0)
        self.assertEqual(response.data["data"]["eventIds"], [])

    def test_face_recognized_is_canonical_and_broadcast(self):
        from unittest.mock import patch

        with patch("apps.ai_results.views.async_to_sync") as sync_mock:
            sync_mock.return_value.return_value = None
            response = self.client.post(
                "/api/ai-results/report/",
                {
                    "cameraId": self.camera.id,
                    "frameId": "face-frame",
                    "timestamp": "2026-07-07T10:00:00+08:00",
                    "results": [{
                        "type": "FACE_RECOGNIZED",
                        "trackId": "t-face",
                        "employeeId": 4,
                        "name": "Employee 4",
                        "similarity": 0.82,
                    }],
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.get().event_type, "face_recognized")
        self.assertEqual(response.data["data"]["acceptedResults"], 1)
        sync_mock.assert_called_once()
        call = sync_mock.return_value.call_args
        self.assertEqual(call.args[0], f"realtime_{self.camera.id}")
        pushed_payload = call.args[1]["data"]["payload"]
        self.assertEqual(pushed_payload["eventType"], "face_recognized")
        self.assertEqual(pushed_payload["name"], "Employee 4")
        self.assertEqual(pushed_payload["confidence"], 0.82)
        self.assertEqual(pushed_payload["description"], "Employee 4 置信度 82.0%")

    def test_person_detection_cannot_spoof_actionable_event_type(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": self.camera.id,
                "frameId": "person-spoof",
                "timestamp": "2026-07-07T10:00:00+08:00",
                "results": [{
                    "type": "PERSON_DETECTION",
                    "eventType": "face_recognized",
                    "trackId": "t-person",
                    "employeeId": 4,
                    "matched": True,
                }],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["acceptedResults"], 0)
        self.assertEqual(response.data["data"]["rejectedResults"], 1)
        self.assertEqual(Event.objects.count(), 0)

    def test_face_recognized_is_deduplicated_across_fragmented_tracks(self):
        from unittest.mock import patch

        def report(timestamp, track_id):
            return self.client.post(
                "/api/ai-results/report/",
                {
                    "cameraId": self.camera.id,
                    "frameId": f"face-{track_id}",
                    "timestamp": timestamp,
                    "results": [{
                        "type": "FACE_RECOGNIZED",
                        "eventType": "face_recognized",
                        "trackId": track_id,
                        "employeeId": 4,
                        "name": "Employee 4",
                        "similarity": 0.82,
                    }],
                },
                format="json",
            )

        with patch("apps.ai_results.views.async_to_sync") as sync_mock:
            sync_mock.return_value.return_value = None
            first = report("2026-07-07T10:00:00+08:00", "t-1")
            duplicate = report("2026-07-07T10:00:30+08:00", "t-2")
            after_cooldown = report("2026-07-07T10:01:01+08:00", "t-3")

        self.assertEqual(first.data["data"]["acceptedResults"], 1)
        self.assertEqual(duplicate.data["data"]["acceptedResults"], 0)
        self.assertEqual(duplicate.data["data"]["rejectedResults"], 1)
        self.assertEqual(after_cooldown.data["data"]["acceptedResults"], 1)
        self.assertEqual(Event.objects.filter(event_type="face_recognized").count(), 2)
        self.assertEqual(sync_mock.call_count, 2)

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
        self.assertEqual(event.event_type, "helmet_violation")
        self.assertEqual(event.confidence, 0.91)
        self.assertEqual(event.snapshot_path, "events/cam-a/frame-0002.jpg")
        self.assertEqual(event.severity, "high")
        self.assertEqual(alert.event, event)
        self.assertEqual(alert.level, "high")
        self.assertEqual(alert.status, Alert.Status.PENDING)

    def test_region_intrusion_alert_uses_region_name_without_track_id(self):
        from unittest.mock import patch

        with patch("apps.ai_results.views.async_to_sync") as sync_mock:
            sync_mock.return_value.return_value = None
            response = self.client.post(
                "/api/ai-results/report/",
                {
                    "cameraId": self.camera.code,
                    "frameId": "region-frame",
                    "timestamp": "2026-07-07T10:02:00+08:00",
                    "results": [
                        {
                            "type": "ZONE_WARNING",
                            "eventType": "region_intrusion",
                            "trackId": "t-49",
                            "regionId": 13,
                            "zoneName": "一号车间入口禁区",
                            "confidence": 0.869,
                        }
                    ],
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["acceptedResults"], 1)
        event = Event.objects.get()
        alert = Alert.objects.get()
        self.assertEqual(event.event_type, "region_intrusion")
        self.assertEqual(alert.description, "区域：一号车间入口禁区")
        self.assertNotIn("trackId", alert.description)
        pushed_payload = sync_mock.return_value.call_args.args[1]["data"]["payload"]
        self.assertEqual(pushed_payload["eventType"], "region_intrusion")
        self.assertEqual(pushed_payload["zoneName"], "一号车间入口禁区")
        self.assertEqual(pushed_payload["regionName"], "一号车间入口禁区")
        self.assertEqual(pushed_payload["regionId"], 13)
        self.assertEqual(pushed_payload["description"], "区域：一号车间入口禁区")

    def test_alert_detail_returns_replay_trajectory_region_and_media_placeholder(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": self.camera.code,
                "frameId": "replay-frame",
                "timestamp": "2026-07-07T10:03:00+08:00",
                "results": [
                    {
                        "type": "ZONE_WARNING",
                        "eventType": "region_intrusion",
                        "trackId": "t-49",
                        "regionId": 13,
                        "regionName": "Restricted Gate",
                        "regionPoints": [{"x": 10, "y": 10}, {"x": 90, "y": 10}, {"x": 90, "y": 90}],
                        "trajectory": [
                            {
                                "timestamp": "2026-07-07T10:02:59+08:00",
                                "center": [20, 30],
                                "bbox": [10, 10, 30, 50],
                                "speed": 4.2,
                                "frameIndex": 12,
                            }
                        ],
                        "triggerPoint": [20, 30],
                        "keyframePath": "event_media/cam-a/replay-frame.jpg",
                        "confidence": 0.869,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        alert_id = response.data["data"]["alertIds"][0]

        detail_response = self.client.get(f"/api/alerts/{alert_id}/detail/")

        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.data["data"]
        self.assertEqual(detail["event"]["eventType"], "region_intrusion")
        self.assertEqual(detail["event"]["trackId"], "t-49")
        self.assertEqual(detail["replay"]["region"]["name"], "Restricted Gate")
        self.assertEqual(detail["replay"]["region"]["points"][0], [10.0, 10.0])
        self.assertEqual(detail["replay"]["trajectory"][0]["center"], [20.0, 30.0])
        self.assertEqual(detail["replay"]["triggerPoint"], [20.0, 30.0])
        self.assertEqual(detail["replay"]["media"]["keyframePath"], "event_media/cam-a/replay-frame.jpg")
        self.assertNotIn("frame", detail["event"]["payload"])

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
