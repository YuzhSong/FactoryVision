from django.test import SimpleTestCase

from .views import FACE_FEATURE_DIMENSION, _validate_feature_payload


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
