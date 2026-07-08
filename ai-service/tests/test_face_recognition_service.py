import tempfile
import unittest
from pathlib import Path

import numpy as np

from modules.face_recognition_service import FaceRecognitionService, _should_use_base_url
from modules.liveness_detector import LivenessResult


class FaceRecognitionServiceTests(unittest.TestCase):
    """Test face-library loading and matching helpers."""

    def test_load_face_library_expands_employee_face_features(self):
        """Verify nested faceFeatures become employee FaceRecord entries."""
        service = FaceRecognitionService(similarity_threshold=0.45)

        result = service.load_face_library(
            employee_items=[
                {
                    "id": 1,
                    "employeeNo": "E001",
                    "name": "Zhang San",
                    "faceFeatures": [
                        {"id": 100, "featureVector": [1.0, 0.0, 0.0]},
                        {"id": 101, "featureVector": [0.0, 1.0, 0.0]},
                    ],
                }
            ]
        )

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["errors"], [])
        self.assertEqual(service.face_records[0].employee_id, 1)
        self.assertEqual(service.face_records[0].employee_no, "E001")

    def test_match_returns_best_employee_feature(self):
        """Verify best cosine-similarity employee is selected."""
        service = FaceRecognitionService(similarity_threshold=0.45)
        service.load_face_library(
            records=[
                {"employeeId": 1, "employeeNo": "E001", "featureVector": [1.0, 0.0, 0.0]},
                {"employeeId": 2, "employeeNo": "E002", "featureVector": [0.0, 1.0, 0.0]},
            ]
        )

        match, similarity = service._match(np.asarray([1.0, 0.0, 0.0], dtype="float32"))

        self.assertEqual(match.employee_id, 1)
        self.assertGreater(similarity, 0.99)

    def test_classify_match_rejects_ambiguous_second_best_score(self):
        """Verify close first and second scores are rejected as unknown."""
        service = FaceRecognitionService(similarity_threshold=0.45, min_score_margin=0.03)
        service.load_face_library(
            records=[
                {"employeeId": 1, "employeeNo": "E001", "featureVector": [1.0, 0.0, 0.0]},
                {"employeeId": 2, "employeeNo": "E002", "featureVector": [0.999, 0.045, 0.0]},
            ]
        )

        match, similarity, decision = service._classify_match(np.asarray([1.0, 0.0, 0.0], dtype="float32"))

        self.assertEqual(match.employee_id, 1)
        self.assertGreater(similarity, 0.99)
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["rejectReason"], "ambiguous_match")

    def test_classify_match_applies_sparse_sample_penalty(self):
        """Verify employees with too few samples need a higher similarity score."""
        service = FaceRecognitionService(
            similarity_threshold=0.45,
            min_samples_per_employee=2,
            sparse_sample_threshold_penalty=0.1,
        )
        service.load_face_library(
            records=[
                {"employeeId": 1, "employeeNo": "E001", "featureVector": [0.5, 0.8660254, 0.0]},
            ]
        )

        match, similarity, decision = service._classify_match(np.asarray([1.0, 0.0, 0.0], dtype="float32"))

        self.assertEqual(match.employee_id, 1)
        self.assertAlmostEqual(similarity, 0.5, places=4)
        self.assertEqual(decision["threshold"], 0.55)
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["rejectReason"], "below_threshold")

    def test_enrollment_quality_rejects_low_confidence_face(self):
        """Verify low-quality enrollment faces are rejected before feature extraction."""
        service = FaceRecognitionService(enrollment_min_quality_score=0.8)
        fake_face = type("Face", (), {"det_score": 0.7, "bbox": [0, 0, 100, 100]})()

        with self.assertRaises(ValueError):
            service._validate_enrollment_face(fake_face)

    def test_existing_relative_file_takes_precedence_over_image_base_url(self):
        """Verify local relative file wins over configured image base URL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            (base_dir / "employee.jpg").write_bytes(b"not-a-real-image")

            should_use_base_url = _should_use_base_url(
                "employee.jpg",
                "http://backend.example/media/",
                base_dir,
            )

        self.assertFalse(should_use_base_url)

    def test_upsert_and_delete_face_records_update_library(self):
        """Verify employee cache upsert replaces stale feature records."""
        service = FaceRecognitionService(similarity_threshold=0.45)
        service.load_face_library(
            employee_items=[
                {"id": 1, "employeeNo": "E001", "faceFeatures": [{"featureVector": [1.0, 0.0, 0.0]}]},
                {"id": 2, "employeeNo": "E002", "faceFeatures": [{"featureVector": [0.0, 1.0, 0.0]}]},
            ]
        )

        result = service.upsert_face_library(
            employee_items=[
                {"id": 1, "employeeNo": "E001", "faceFeatures": [{"featureVector": [0.0, 0.0, 1.0]}]},
            ]
        )

        employee_one_records = [record for record in service.face_records if str(record.employee_id) == "1"]
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(employee_one_records), 1)
        self.assertGreater(float(employee_one_records[0].feature[2]), 0.99)

        delete_result = service.delete_face_records(employee_ids=[1])

        self.assertEqual(delete_result["deleted"], 1)
        self.assertEqual(len(service.face_records), 1)
        self.assertEqual(service.face_records[0].employee_no, "E002")

    def test_recognize_rejects_spoof_before_identity_match(self):
        """Verify liveness failure prevents employee matching."""
        liveness_detector = _FakeLivenessDetector(
            LivenessResult(
                enabled=True,
                passed=False,
                score=0.12,
                threshold=0.55,
                method="rgb_heuristic",
                reject_reason="liveness_failed",
            )
        )
        service = _FakeRecognizeService(liveness_detector=liveness_detector)
        service.load_face_library(records=[{"employeeId": 1, "employeeNo": "E001", "featureVector": [1, 0, 0]}])

        results = service.recognize(np.zeros((100, 100, 3), dtype=np.uint8), frame_id="frame-1")

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["matched"])
        self.assertEqual(results[0]["label"], "spoof")
        self.assertEqual(results[0]["rejectReason"], "liveness_failed")
        self.assertFalse(results[0]["livenessPassed"])
        self.assertFalse(service.embedding_called)

    def test_recognize_includes_liveness_metadata_when_passed(self):
        """Verify passed liveness still allows normal identity matching."""
        liveness_detector = _FakeLivenessDetector(
            LivenessResult(
                enabled=True,
                passed=True,
                score=0.91,
                threshold=0.55,
                method="rgb_heuristic",
            )
        )
        service = _FakeRecognizeService(liveness_detector=liveness_detector)
        service.load_face_library(records=[{"employeeId": 1, "employeeNo": "E001", "featureVector": [1, 0, 0]}])

        results = service.recognize(np.zeros((100, 100, 3), dtype=np.uint8), frame_id="frame-1")

        self.assertTrue(results[0]["matched"])
        self.assertTrue(results[0]["livenessPassed"])
        self.assertEqual(results[0]["livenessScore"], 0.91)
        self.assertTrue(service.embedding_called)

    def test_enrollment_can_require_liveness(self):
        """Verify enrollment rejects a spoof when strict liveness is enabled."""
        liveness_detector = _FakeLivenessDetector(
            LivenessResult(
                enabled=True,
                passed=False,
                score=0.1,
                threshold=0.55,
                method="rgb_heuristic",
                reject_reason="liveness_failed",
            )
        )
        service = _FakeRecognizeService(
            liveness_detector=liveness_detector,
            liveness_require_for_enrollment=True,
        )

        with self.assertRaises(ValueError):
            service.extract_feature_details(np.zeros((100, 100, 3), dtype=np.uint8))

class _FakeFace:
    bbox = [10, 10, 90, 90]
    det_score = 0.99


class _FakeLivenessDetector:
    def __init__(self, result):
        self.result = result

    def predict(self, _face_crop):
        return self.result

    def status(self):
        return {"enabled": self.result.enabled, "threshold": self.result.threshold}


class _FakeRecognizeService(FaceRecognitionService):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, similarity_threshold=0.45, **kwargs)
        self.embedding_called = False

    def _detect_faces(self, _frame):
        return [_FakeFace()]

    def _face_embedding(self, _face):
        self.embedding_called = True
        return np.asarray([1.0, 0.0, 0.0], dtype="float32")


if __name__ == "__main__":
    unittest.main()
