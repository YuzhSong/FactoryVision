from datetime import datetime, timezone


class EmployeeRecognitionDetector:
    """Emit one face-recognition event per continuous track with employee cooldown."""

    def __init__(self, employee_cooldown_seconds=60.0, track_ttl_seconds=30.0):
        self.employee_cooldown_seconds = max(0.0, float(employee_cooldown_seconds or 0))
        self.track_ttl_seconds = max(1.0, float(track_ttl_seconds or 1))
        self._track_states = {}
        self._employee_reported_at = {}

    def detect(self, face_results, camera_id=None, frame_id=None, timestamp=None):
        timestamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat()
        now = _timestamp_seconds(timestamp)
        self._purge(now)
        events = []
        for result in face_results or []:
            if result.get("type") != "FACE_RESULT" or result.get("matched") is not True:
                continue
            employee_id = result.get("employeeId")
            track_id = result.get("trackId")
            if employee_id in (None, "") or track_id in (None, "") or camera_id in (None, ""):
                continue

            track_key = (str(camera_id), str(track_id), str(employee_id))
            employee_key = (str(camera_id), str(employee_id))
            state = self._track_states.get(track_key)
            if state is not None:
                state["lastSeenAt"] = now
                continue

            self._track_states[track_key] = {"firstSeenAt": now, "lastSeenAt": now}
            previous = self._employee_reported_at.get(employee_key)
            if previous is not None and now - previous < self.employee_cooldown_seconds:
                continue

            self._employee_reported_at[employee_key] = now
            employee_name = result.get("name") or result.get("employeeName") or "Unknown"
            confidence = _coerce_float(result.get("confidence"))
            if confidence is None:
                confidence = _coerce_float(result.get("similarity"))
            description = _face_description(employee_name, confidence)
            events.append({
                "type": "FACE_RECOGNIZED",
                "eventType": "face_recognized",
                "cameraId": camera_id,
                "frameId": frame_id,
                "trackId": track_id,
                "employeeId": employee_id,
                "employeeNo": result.get("employeeNo"),
                "employeeName": employee_name,
                "name": employee_name,
                "confidence": confidence,
                "similarity": result.get("similarity"),
                "threshold": result.get("threshold"),
                "secondBestSimilarity": result.get("secondBestSimilarity"),
                "scoreMargin": result.get("scoreMargin"),
                "faceBox": result.get("faceBox"),
                "description": description,
                "timestamp": timestamp,
                "level": "info",
            })
        return events

    def observe_tracks(self, camera_id, track_ids, timestamp=None):
        now = _timestamp_seconds(timestamp or datetime.now(timezone.utc).astimezone().isoformat())
        visible = {str(value) for value in track_ids if value not in (None, "")}
        for key, state in self._track_states.items():
            if key[0] == str(camera_id) and key[1] in visible:
                state["lastSeenAt"] = now
        self._purge(now)

    def reset(self):
        self._track_states.clear()
        self._employee_reported_at.clear()

    def status(self):
        return {
            "trackStates": len(self._track_states),
            "employeeCooldownStates": len(self._employee_reported_at),
            "employeeCooldownSeconds": self.employee_cooldown_seconds,
            "trackTtlSeconds": self.track_ttl_seconds,
        }

    def _purge(self, now):
        self._track_states = {
            key: value for key, value in self._track_states.items()
            if now - value["lastSeenAt"] <= self.track_ttl_seconds
        }
        retention = max(self.employee_cooldown_seconds, self.track_ttl_seconds)
        self._employee_reported_at = {
            key: value for key, value in self._employee_reported_at.items()
            if now - value <= retention
        }


def _timestamp_seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    normalized = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return datetime.now(timezone.utc).timestamp()


def _coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _face_description(name, confidence):
    if confidence is None:
        return str(name)
    if confidence <= 1.0:
        return f"{name} 置信度 {confidence * 100:.1f}%"
    return f"{name} 置信度 {confidence:.1f}%"
