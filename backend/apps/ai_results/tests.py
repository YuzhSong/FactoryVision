from django.test import TestCase
from rest_framework.test import APIClient


class AIResultsReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_report_endpoint_accepts_valid_payload(self):
        response = self.client.post(
            "/api/ai-results/report/",
            {
                "cameraId": 1,
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
        self.assertEqual(response.data["data"]["cameraId"], 1)
        self.assertEqual(response.data["data"]["frameId"], "frame-0001")

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
