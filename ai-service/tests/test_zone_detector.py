import unittest

from modules.zone_detector import ZoneDetector


def _person(track_id="t-1", x=50, y=50):
    return {
        "type": "PERSON_DETECTION",
        "trackId": track_id,
        "footPoint": {"x": x, "y": y},
    }


def _zone(**kwargs):
    zone = {
        "id": 1,
        "name": "Danger Zone",
        "points": [
            {"x": 0, "y": 0},
            {"x": 100, "y": 0},
            {"x": 100, "y": 100},
            {"x": 0, "y": 100},
        ],
        "safeDistance": 10,
    }
    zone.update(kwargs)
    return zone


class ZoneDetectorTests(unittest.TestCase):
    def test_zone_warning_requires_ten_second_stay_by_default(self):
        detector = ZoneDetector(zones=[_zone()], min_stay_seconds=10)

        first = detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:00+08:00")
        nine_seconds = detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:09+08:00")
        ten_seconds = detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:10+08:00")

        self.assertEqual(first, [])
        self.assertEqual(nine_seconds, [])
        self.assertEqual(len(ten_seconds), 1)
        self.assertEqual(ten_seconds[0]["type"], "ZONE_WARNING")
        self.assertEqual(ten_seconds[0]["staySeconds"], 10.0)
        self.assertEqual(ten_seconds[0]["minStaySeconds"], 10.0)

    def test_zone_specific_min_stay_seconds_overrides_default(self):
        detector = ZoneDetector(zones=[_zone(minStaySeconds=3)], min_stay_seconds=10)

        detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:00+08:00")
        warning = detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:03+08:00")

        self.assertEqual(len(warning), 1)
        self.assertEqual(warning[0]["minStaySeconds"], 3.0)

    def test_zone_state_resets_after_person_leaves_safe_range(self):
        detector = ZoneDetector(zones=[_zone()], min_stay_seconds=10)

        detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:00+08:00")
        detector.detect_intrusion([_person(x=200, y=200)], timestamp="2026-07-09T10:00:05+08:00")
        warning = detector.detect_intrusion([_person()], timestamp="2026-07-09T10:00:11+08:00")

        self.assertEqual(warning, [])

    def test_safe_distance_stay_also_requires_min_duration(self):
        detector = ZoneDetector(zones=[_zone()], min_stay_seconds=10)
        near_edge = _person(x=105, y=50)

        detector.detect_intrusion([near_edge], timestamp="2026-07-09T10:00:00+08:00")
        warning = detector.detect_intrusion([near_edge], timestamp="2026-07-09T10:00:10+08:00")

        self.assertEqual(len(warning), 1)
        self.assertFalse(warning[0]["inside"])
        self.assertEqual(warning[0]["distance"], 5.0)
        self.assertEqual(warning[0]["level"], "medium")


if __name__ == "__main__":
    unittest.main()
