import math
from datetime import datetime


class RunningDetector:
    """Detect running from movement speed across recent track history."""

    def __init__(self, speed_threshold: float = 30.0, confirm_frames: int = 5):
        """Initialize running detector with speed_threshold and confirm_frames."""
        self.speed_threshold = speed_threshold
        self.confirm_frames = confirm_frames

    def detect(self, track_history):
        """Return RUNNING_ALERT-style result from one track history."""
        recent_history = self._get_recent_history(track_history)
        if len(recent_history) < 2:
            return None

        speeds = self._calculate_speeds(recent_history)
        if not speeds:
            return None

        over_threshold = [speed for speed in speeds if speed >= self.speed_threshold]
        is_running = len(over_threshold) >= max(1, self.confirm_frames - 1)
        latest = recent_history[-1]
        pixel_speed = speeds[-1]

        return {
            "type": "RUNNING_ALERT",
            "event_type": "running",
            "trackId": latest.get("trackId"),
            "isRunning": is_running,
            "pixelSpeed": round(pixel_speed, 2),
            "speed": round(pixel_speed, 2),
            "threshold": self.speed_threshold,
            "durationFrames": len(over_threshold),
            "level": self._get_level(is_running, pixel_speed),
            "bbox": latest.get("bbox"),
            "confidence": 0.85 if is_running else 0.0,
            "message": "检测到疑似奔跑行为" if is_running else "未检测到奔跑行为",
        }

    def _get_recent_history(self, track_history):
        """Keep only recent frames needed for running confirmation."""
        if not track_history:
            return []
        return list(track_history)[-self.confirm_frames :]

    def _calculate_speeds(self, history):
        """Calculate pixel speeds between adjacent history entries."""
        speeds = []
        for previous, current in zip(history, history[1:]):
            previous_point = self._get_point(previous)
            current_point = self._get_point(current)
            if previous_point is None or current_point is None:
                continue

            elapsed_seconds = self._get_elapsed_seconds(previous, current)
            if elapsed_seconds <= 0:
                elapsed_seconds = 1.0

            distance = math.dist(previous_point, current_point)
            speeds.append(distance / elapsed_seconds)

        return speeds

    def _get_point(self, entry):
        """Extract center or foot point from one history entry."""
        point = entry.get("center") or entry.get("centerPoint") or entry.get("footPoint")
        if isinstance(point, dict):
            return (point.get("x", 0), point.get("y", 0))
        if isinstance(point, (list, tuple)) and len(point) == 2:
            return (point[0], point[1])

        bbox = entry.get("bbox")
        if isinstance(bbox, dict):
            return ((bbox.get("x1", 0) + bbox.get("x2", 0)) / 2, (bbox.get("y1", 0) + bbox.get("y2", 0)) / 2)
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            return ((x1 + x2) / 2, (y1 + y2) / 2)

        return None

    def _get_elapsed_seconds(self, previous, current):
        """Calculate elapsed seconds from timestamps or frameIndex/fps."""
        previous_timestamp = previous.get("timestamp") or previous.get("time")
        current_timestamp = current.get("timestamp") or current.get("time")

        parsed_previous_timestamp = self._parse_timestamp(previous_timestamp)
        parsed_current_timestamp = self._parse_timestamp(current_timestamp)
        if parsed_previous_timestamp is not None and parsed_current_timestamp is not None:
            return parsed_current_timestamp - parsed_previous_timestamp

        previous_frame_id = previous.get("frameIndex")
        current_frame_id = current.get("frameIndex")
        fps = current.get("fps") or previous.get("fps") or 1
        if isinstance(previous_frame_id, int) and isinstance(current_frame_id, int) and fps > 0:
            return (current_frame_id - previous_frame_id) / fps

        return 1.0

    def _parse_timestamp(self, value):
        """Parse numeric or ISO timestamp into epoch seconds."""
        if isinstance(value, (int, float)):
            return float(value)

        if not isinstance(value, str) or not value.strip():
            return None

        normalized_value = value.strip()
        if normalized_value.endswith("Z"):
            normalized_value = f"{normalized_value[:-1]}+00:00"

        try:
            return datetime.fromisoformat(normalized_value).timestamp()
        except ValueError:
            return None

    def _get_level(self, is_running, pixel_speed):
        """Map running state and pixel_speed to alert level."""
        if not is_running:
            return "low"
        if pixel_speed >= self.speed_threshold * 1.5:
            return "high"
        return "medium"
