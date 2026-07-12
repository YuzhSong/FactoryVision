import unittest

from modules.event_types import normalize_event_result, normalize_event_type


class EventTypeTests(unittest.TestCase):
    def test_legacy_types_map_to_formal_contract(self):
        cases = [
            ({"type": "HELMET_WARNING"}, "helmet_violation"),
            ({"type": "ZONE_WARNING", "eventType": "region_dwell"}, "region_dwell"),
            ({"type": "ZONE_WARNING", "eventType": "region_intrusion"}, "region_intrusion"),
            ({"type": "FACE_RESULT"}, "face_recognized"),
            ({"type": "STRANGER_ALERT"}, "stranger_detected"),
        ]
        for payload, expected in cases:
            self.assertEqual(normalize_event_type(payload), expected)
            self.assertEqual(normalize_event_result(payload)["eventType"], expected)


if __name__ == "__main__":
    unittest.main()
