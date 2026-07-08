import tempfile
import unittest
from pathlib import Path

import numpy as np

from modules.face_recognition_service import FaceRecognitionService, _should_use_base_url


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


if __name__ == "__main__":
    unittest.main()
