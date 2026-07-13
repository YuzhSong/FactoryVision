import unittest

from modules.abnormal_behavior_service import AbnormalBehaviorService


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def person(track_id="t1", status="no_helmet", confidence=.9):
    return {"trackId": track_id, "helmetStatus": status, "helmetConfidence": confidence, "bbox": {}}


class HelmetCooldownTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.service = AbnormalBehaviorService(config={
            "clock": self.clock,
            "helmetEventCooldownSeconds": 20,
            "trackStateTtlSeconds": 5,
        })

    def event(self, camera=1, detection=None):
        report = self.service.build_ai_report(camera, "f", [detection or person()])
        return next((item for item in report["results"] if item.get("type") == "HELMET_WARNING"), None)

    def test_cooldown_reset_unknown_and_isolation(self):
        self.assertIsNotNone(self.event())
        self.clock.now = 19.9
        self.assertIsNone(self.event())
        self.clock.now = 20
        self.assertIsNotNone(self.event())
        self.assertIsNotNone(self.event(camera=2))
        self.assertIsNotNone(self.event(detection=person("t2")))
        self.assertIsNone(self.event(detection=person(status="unknown")))
        self.assertIsNone(self.event(detection=person(status="helmet")))
        self.assertIsNotNone(self.event())

    def test_track_ttl_clears_violation(self):
        self.assertIsNotNone(self.event())
        self.clock.now = 6
        self.service.build_ai_report(1, "missing", [])
        self.assertIsNotNone(self.event())


if __name__ == "__main__":
    unittest.main()
