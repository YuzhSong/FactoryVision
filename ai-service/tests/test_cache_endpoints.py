import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient

    import app as app_module
    from modules.runtime_cache import RuntimeCache
except ModuleNotFoundError as exc:
    if exc.name == "fastapi":
        raise unittest.SkipTest("fastapi is not installed; run pip install -r requirements.txt")
    raise


class _FakeFaceService:
    """Fake face service for endpoint-level cache tests."""

    def __init__(self):
        self.loaded_employees = []
        self.upserted = []
        self.deleted = []

    def status(self):
        return {"loadedFaces": len(self.loaded_employees), "modelLoaded": False}

    def load_face_library(self, employee_items=None, **_kwargs):
        self.loaded_employees = employee_items or []
        return {"count": len(self.loaded_employees), "errors": []}

    def upsert_face_library(self, records=None, employee_items=None, **_kwargs):
        self.upserted = (records or []) + (employee_items or [])
        return {"count": len(self.upserted), "errors": [], "updatedEmployees": len(self.upserted)}

    def delete_face_records(self, employee_ids=None, employee_nos=None):
        self.deleted = {"employeeIds": employee_ids or [], "employeeNos": employee_nos or []}
        return {"deleted": len(self.deleted["employeeIds"]) + len(self.deleted["employeeNos"]), "count": 0}

    def extract_feature_details(self, image, **kwargs):
        return {
            "image": image,
            "faceCount": 1,
            "featureVector": [1.0] + [0.0] * 511,
            "dimension": 3,
            "qualityScore": 0.99,
            "faceBox": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
            "requireSingleFace": kwargs.get("require_single_face"),
        }


class _FakeBackendClient:
    """Fake backend client for bootstrap and cache reload tests."""

    def get_bootstrap(self):
        return {
            "code": 200,
            "data": {
                "version": "v1",
                "employees": [{"id": 1, "employeeNo": "E001", "faceFeatures": []}],
                "cameras": [{"id": 1, "streamUrl": "rtmp://source/live/1"}],
                "zones": [{"id": 10, "cameraId": 1, "points": []}],
                "settings": {"runningSpeedThreshold": 120},
            },
        }

    def list_cameras(self, status="online"):
        return [{"id": 2, "status": status, "streamUrl": "rtmp://source/live/2"}]

    def list_zones(self, camera_id):
        return [{"id": 20, "cameraId": camera_id, "points": []}]


class CacheEndpointTests(unittest.TestCase):
    """Test AI-side cache and face enrollment endpoints."""

    def test_extract_face_feature_accepts_image_url_payload(self):
        fake_face_service = _FakeFaceService()

        with patch.object(app_module, "face_service", fake_face_service):
            response = TestClient(app_module.app).post(
                "/faces/extract",
                json={"employeeId": 1, "imageUrl": "http://backend/media/face.jpg"},
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["employeeId"], 1)
        self.assertEqual(payload["data"]["dimension"], 3)
        self.assertEqual(payload["data"]["image"], "http://backend/media/face.jpg")

    def test_employee_cache_upsert_and_delete_endpoints(self):
        fake_face_service = _FakeFaceService()

        with patch.object(app_module, "face_service", fake_face_service):
            client = TestClient(app_module.app)
            upsert_response = client.post(
                "/cache/employees/upsert",
                json={"employee": {"id": 1, "employeeNo": "E001", "faceFeatures": []}},
            )
            delete_response = client.post("/cache/employees/delete", json={"employeeId": 1})

        self.assertEqual(upsert_response.status_code, 200)
        self.assertEqual(upsert_response.json()["data"]["updatedEmployees"], 1)
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(fake_face_service.deleted["employeeIds"], [1])

    def test_cache_reload_loads_backend_bootstrap(self):
        fake_face_service = _FakeFaceService()
        fake_backend_client = _FakeBackendClient()
        runtime_cache = RuntimeCache()

        with patch.object(app_module, "face_service", fake_face_service), patch.object(
            app_module, "backend_client", fake_backend_client
        ), patch.object(app_module, "runtime_cache", runtime_cache):
            response = TestClient(app_module.app).post("/cache/reload", json={"source": "backend"})

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["data"]["runtimeCache"]["cacheReady"])
        self.assertEqual(payload["data"]["runtimeCache"]["cameraCount"], 1)
        self.assertEqual(payload["data"]["runtimeCache"]["zoneCount"], 1)
        self.assertEqual(payload["data"]["faceLibrary"]["count"], 1)

    def test_camera_and_zone_reload_can_use_backend_client(self):
        fake_backend_client = _FakeBackendClient()
        runtime_cache = RuntimeCache()

        with patch.object(app_module, "backend_client", fake_backend_client), patch.object(
            app_module, "runtime_cache", runtime_cache
        ):
            client = TestClient(app_module.app)
            camera_response = client.post("/cache/cameras/reload", json={"source": "backend"})
            zone_response = client.post("/cache/zones/reload", json={"source": "backend", "cameraId": 2})

        self.assertEqual(camera_response.status_code, 200)
        self.assertEqual(camera_response.json()["data"]["cameraCount"], 1)
        self.assertEqual(zone_response.status_code, 200)
        self.assertEqual(zone_response.json()["data"]["zoneCount"], 1)


if __name__ == "__main__":
    unittest.main()
