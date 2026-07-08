import unittest

import app as app_module
from ai_config import Config


class AppConfigWiringTests(unittest.TestCase):
    """Guard app-level wiring for features configured outside modules."""

    def test_face_liveness_config_is_wired_into_face_service(self):
        liveness_status = app_module.face_service.status()["liveness"]

        self.assertEqual(liveness_status["enabled"], Config.FACE_LIVENESS_ENABLED)
        self.assertEqual(liveness_status["threshold"], Config.FACE_LIVENESS_THRESHOLD)
        self.assertEqual(liveness_status["minFaceSize"], Config.FACE_LIVENESS_MIN_FACE_SIZE)
        self.assertEqual(
            app_module.face_service.liveness_require_for_enrollment,
            Config.FACE_LIVENESS_REQUIRE_FOR_ENROLLMENT,
        )

    def test_zone_timing_config_is_wired_into_frame_processor(self):
        zone_detector = app_module.frame_processor.abnormal_service.zone_detector

        self.assertEqual(zone_detector.min_stay_seconds, Config.ZONE_MIN_STAY_SECONDS)
        self.assertEqual(zone_detector.state_ttl_seconds, Config.ZONE_STATE_TTL_SECONDS)


if __name__ == "__main__":
    unittest.main()
