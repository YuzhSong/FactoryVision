ABNORMAL_BEHAVIOR = "abnormal_behavior"
EMERGENCY_EVENT = "emergency_event"


EMERGENCY_TYPES = {
    "FALL_ALERT",
    "FIRE_ALERT",
    "SMOKE_ALERT",
    "WATER_LEAK_ALERT",
    "FLOODING_ALERT",
}

ABNORMAL_TYPES = {
    "HELMET_WARNING",
    "ZONE_WARNING",
    "RUNNING_ALERT",
    "STRANGER_ALERT",
    "EMPLOYEE_PRESENCE_EVENT",
}


def enrich_event_classification(results):
    """Add machine-readable event category to alert-like results."""
    enriched = []
    for result in results or []:
        if isinstance(result, dict):
            _enrich_result(result)
        enriched.append(result)
    return enriched


def classify_result(result):
    """Return event category metadata for one AI result, or None for non-alert results."""
    result_type = result.get("type") if isinstance(result, dict) else None
    if result_type in EMERGENCY_TYPES:
        return {"category": EMERGENCY_EVENT}
    if result_type in ABNORMAL_TYPES:
        return {"category": ABNORMAL_BEHAVIOR}
    return None


def _enrich_result(result):
    classification = classify_result(result)
    if not classification:
        return
    for key, value in classification.items():
        result.setdefault(key, value)
