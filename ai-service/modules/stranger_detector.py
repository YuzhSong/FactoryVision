from datetime import datetime, timezone
import math


class StrangerDetector:
    """Confirm unknown faces across frames and suppress repeated alerts."""

    def __init__(
        self,
        confirm_frames: int = 3,
        cooldown_seconds: float = 30.0,
        match_distance_threshold: float = 80.0,
        state_ttl_seconds: float = 10.0,
    ):
        self.confirm_frames = max(1, int(confirm_frames or 1))
        self.cooldown_seconds = max(0.0, float(cooldown_seconds or 0))
        self.match_distance_threshold = max(0.0, float(match_distance_threshold or 0))
        self.state_ttl_seconds = max(1.0, float(state_ttl_seconds or 1))
        self._states = []
        self._next_id = 1

    def detect(self, face_results, camera_id=None, frame_id=None, timestamp=None):
        """Return confirmed STRANGER_ALERT results from FACE_RESULT unknowns."""
        timestamp = timestamp or _now_iso()
        now_seconds = _timestamp_seconds(timestamp)
        self._purge_expired(now_seconds)

        alerts = []
        for face_result in face_results or []:
            if not _is_unknown_face(face_result):
                continue

            face_box = face_result.get("faceBox") or face_result.get("bbox")
            if not face_box:
                continue

            state = self._find_state(face_box, camera_id, now_seconds)
            state["count"] += 1
            state["lastSeenAt"] = timestamp
            state["lastSeenSeconds"] = now_seconds
            state["faceBox"] = dict(face_box)
            state["lastFaceResult"] = face_result

            if state["count"] < self.confirm_frames:
                continue
            if now_seconds - state.get("lastAlertSeconds", -math.inf) < self.cooldown_seconds:
                continue

            state["lastAlertSeconds"] = now_seconds
            state["lastAlertAt"] = timestamp
            alerts.append(self._build_alert(state, camera_id, frame_id, timestamp))

        return alerts

    def reset(self):
        """Clear stranger confirmation state."""
        self._states = []
        self._next_id = 1

    def _find_state(self, face_box, camera_id, now_seconds):
        center = _box_center(face_box)
        best_state = None
        best_distance = math.inf
        for state in self._states:
            if str(state.get("cameraId")) != str(camera_id):
                continue
            distance = math.dist(center, state["center"])
            if distance < best_distance:
                best_distance = distance
                best_state = state

        if best_state is not None and best_distance <= self.match_distance_threshold:
            best_state["center"] = center
            return best_state

        state = {
            "strangerTrackId": f"stranger-{self._next_id}",
            "cameraId": camera_id,
            "center": center,
            "count": 0,
            "firstSeenSeconds": now_seconds,
            "lastSeenSeconds": now_seconds,
            "lastAlertSeconds": -math.inf,
        }
        self._next_id += 1
        self._states.append(state)
        return state

    def _purge_expired(self, now_seconds):
        self._states = [
            state
            for state in self._states
            if now_seconds - state.get("lastSeenSeconds", now_seconds) <= self.state_ttl_seconds
        ]

    def _build_alert(self, state, camera_id, frame_id, timestamp):
        face_result = state.get("lastFaceResult") or {}
        return {
            "type": "STRANGER_ALERT",
            "cameraId": camera_id,
            "frameId": frame_id,
            "timestamp": timestamp,
            "trackId": face_result.get("trackId"),
            "strangerTrackId": state["strangerTrackId"],
            "faceBox": state.get("faceBox"),
            "similarity": face_result.get("similarity"),
            "threshold": face_result.get("threshold"),
            "confirmFrames": self.confirm_frames,
            "observedFrames": state["count"],
            "level": "medium",
        }


def _is_unknown_face(result):
    return result.get("type") == "FACE_RESULT" and result.get("matched") is False


def _box_center(box):
    x1 = float(box.get("x1", 0))
    y1 = float(box.get("y1", 0))
    x2 = float(box.get("x2", 0))
    y2 = float(box.get("y2", 0))
    return [(x1 + x2) / 2, (y1 + y2) / 2]


def _timestamp_seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return datetime.now(timezone.utc).timestamp()

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return datetime.now(timezone.utc).timestamp()


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()
