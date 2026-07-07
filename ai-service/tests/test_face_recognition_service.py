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


if __name__ == "__main__":
    unittest.main()
