FORMAL_EVENT_TYPES = {
    "HELMET_WARNING": "helmet_violation",
    "helmet_violation": "helmet_violation",
    "region_intrusion": "region_intrusion",
    "region_dwell": "region_dwell",
    "FACE_RESULT": "face_recognized",
    "FACE_RECOGNIZED": "face_recognized",
    "face_recognized": "face_recognized",
    "STRANGER_DETECTED": "stranger_detected",
    "STRANGER_ALERT": "stranger_detected",
    "stranger_detected": "stranger_detected",
    "FALL_DETECTED": "fall_detected",
    "FALL_ALERT": "fall_detected",
    "fall_detected": "fall_detected",
}


def normalize_event_type(result):
    """Map legacy AI result names onto the stable external event contract."""
    internal_type = str(result.get("type") or "").strip()
    nested_type = str(result.get("eventType") or "").strip()
    if internal_type == "ZONE_WARNING":
        return FORMAL_EVENT_TYPES.get(nested_type, nested_type or "region_intrusion")
    return FORMAL_EVENT_TYPES.get(nested_type) or FORMAL_EVENT_TYPES.get(internal_type) or nested_type or internal_type


def normalize_event_result(result):
    normalized = dict(result)
    normalized["eventType"] = normalize_event_type(result)
    return normalized
