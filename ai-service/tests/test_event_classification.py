import unittest

from modules.event_classification import (
    ABNORMAL_BEHAVIOR,
    EMERGENCY_EVENT,
    classify_result,
    enrich_event_classification,
)


class EventClassificationTests(unittest.TestCase):
    def test_fall_alert_is_emergency_event(self):
        classification = classify_result({"type": "FALL_ALERT"})

        self.assertEqual(classification["category"], EMERGENCY_EVENT)
        self.assertEqual(set(classification), {"category"})

    def test_common_warnings_are_abnormal_behavior(self):
        for result_type in (
            "HELMET_WARNING",
            "ZONE_WARNING",
            "RUNNING_ALERT",
            "STRANGER_ALERT",
            "EMPLOYEE_PRESENCE_EVENT",
        ):
            with self.subTest(result_type=result_type):
                classification = classify_result({"type": result_type})
                self.assertEqual(classification["category"], ABNORMAL_BEHAVIOR)
                self.assertEqual(set(classification), {"category"})

    def test_enrich_keeps_non_alert_results_unchanged(self):
        results = [{"type": "PERSON_DETECTION"}, {"type": "FALL_ALERT"}]

        enriched = enrich_event_classification(results)

        self.assertNotIn("category", enriched[0])
        self.assertEqual(enriched[1]["category"], EMERGENCY_EVENT)


if __name__ == "__main__":
    unittest.main()
