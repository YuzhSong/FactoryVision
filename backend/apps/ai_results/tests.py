from django.test import TestCase
from rest_framework.test import APIClient

from apps.ai_results.models import AIEvent, Alert
from apps.cameras.models import Camera
from apps.employees.models import Employee
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
        self.assertEqual(AIEvent.objects.count(), 1)
        self.assertEqual(Alert.objects.count(), 0)

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

        event = AIEvent.objects.get()
        alert = Alert.objects.get()
        self.assertEqual(event.camera, self.camera)
        self.assertEqual(event.event_type, "HELMET_WARNING")
        self.assertEqual(event.confidence, 0.91)
        self.assertEqual(event.snapshot_path, "events/cam-a/frame-0002.jpg")
        self.assertEqual(alert.event, event)
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
