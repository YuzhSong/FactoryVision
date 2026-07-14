from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.employees.models import Employee

from .views import FACE_FEATURE_DIMENSION, _validate_feature_payload
from .models import FaceFeature


class FeaturePayloadValidationTests(SimpleTestCase):
    def _payload(self, vector=None, **overrides):
        payload = {
            "faceCount": 1,
            "featureVector": vector if vector is not None else [0.1] * FACE_FEATURE_DIMENSION,
            "dimension": FACE_FEATURE_DIMENSION,
        }
        payload.update(overrides)
        return payload

    def test_accepts_one_finite_512_dimension_embedding(self):
        vector = _validate_feature_payload(self._payload())
        self.assertEqual(len(vector), FACE_FEATURE_DIMENSION)

    def test_rejects_no_face_or_multiple_faces(self):
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(faceCount=0))
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(faceCount=2))

    def test_rejects_wrong_length_and_non_finite_values(self):
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(vector=[0.1], dimension=1))
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(vector=[float("nan")] * FACE_FEATURE_DIMENSION))

    def test_liveness_is_enforced_only_when_configured(self):
        failed_liveness = self._payload(livenessAvailable=False, livenessPassed=None, livenessProvider="rgb_quality_heuristic")
        self.assertEqual(len(_validate_feature_payload(failed_liveness, liveness_required=False)), FACE_FEATURE_DIMENSION)
        with self.assertRaises(ValueError):
            _validate_feature_payload(failed_liveness, liveness_required=True)

    def test_strict_liveness_rejects_missing_or_explicitly_rejected_enrollment(self):
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(), liveness_required=True)
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(enrollmentAccepted=False))

    def test_strict_liveness_requires_a_verified_onnx_pass(self):
        accepted = self._payload(livenessAvailable=True, livenessPassed=True, livenessProvider="onnx")
        self.assertEqual(len(_validate_feature_payload(accepted, liveness_required=True)), FACE_FEATURE_DIMENSION)
        with self.assertRaises(ValueError):
            _validate_feature_payload(self._payload(livenessAvailable=True, livenessPassed=False, livenessProvider="onnx"), liveness_required=True)


@override_settings(AI_SERVICE_API_TOKEN="test-ai-service-token")
class FaceLibraryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.employee = Employee.objects.create(employee_no="FACE-001", name="Face Library User")
        FaceFeature.objects.create(
            employee=self.employee,
            face_type=FaceFeature.FaceType.FRONT,
            feature_vector=[0.1] * FACE_FEATURE_DIMENSION,
            image_path="faces/1/front.jpg",
        )

    def test_library_requires_dedicated_ai_service_token(self):
        response = self.client.get("/api/face/library/")
        self.assertEqual(response.status_code, 403)

    def test_library_returns_active_employee_face_features(self):
        response = self.client.get(
            "/api/face/library/",
            HTTP_X_AI_SERVICE_TOKEN="test-ai-service-token",
        )
        self.assertEqual(response.status_code, 200)
        item = response.data["data"]["items"][0]
        self.assertEqual(item["employeeNo"], "FACE-001")
        self.assertEqual(len(item["faceFeatures"][0]["featureVector"]), FACE_FEATURE_DIMENSION)


class FaceEnrollWithProvidedFeatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(username="face-enroll-admin", password="test-pass-123")
        self.employee = Employee.objects.create(employee_no="FACE-002", name="Provided Feature User")

    def test_enroll_accepts_browser_extracted_features_without_ai_service_call(self):
        self.client.force_authenticate(user=self.user)
        image = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
        response = self.client.post(
            "/api/face/enroll/",
            {
                "employeeId": self.employee.id,
                "faces": [
                    {
                        "faceType": face_type,
                        "imageBase64": image,
                        "featureVector": [0.1] * FACE_FEATURE_DIMENSION,
                        "dimension": FACE_FEATURE_DIMENSION,
                    }
                    for face_type in ("front", "left", "right")
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FaceFeature.objects.filter(employee=self.employee).count(), 3)
