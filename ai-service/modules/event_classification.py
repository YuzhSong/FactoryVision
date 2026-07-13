ABNORMAL_BEHAVIOR = "abnormal_behavior"
EMERGENCY_EVENT = "emergency_event"


EMERGENCY_TYPES = {"FALL_ALERT", "FIRE_ALERT", "SMOKE_ALERT", "WATER_LEAK_ALERT", "FLOODING_ALERT"}
ABNORMAL_TYPES = {
    "HELMET_WARNING",
    "ZONE_WARNING",
    "RUNNING_ALERT",
    "STRANGER_ALERT",
    "EMPLOYEE_PRESENCE_EVENT",
}


def enrich_event_classification(results):
    """Add a stable, optional high-level category to alert-like results."""
    for result in results or []:
        if not isinstance(result, dict) or result.get("category"):
            continue
        result_type = result.get("type")
        if result_type in EMERGENCY_TYPES:
            result["category"] = EMERGENCY_EVENT
        elif result_type in ABNORMAL_TYPES:
            result["category"] = ABNORMAL_BEHAVIOR
    return results
