class FallDetector:
    """Detect possible fall events from recent person bbox history."""

    def __init__(self, ratio_threshold: float = 1.2, confirm_frames: int = 5, min_confidence: float = 0.6):
        """Initialize fall thresholds with ratio, confirm_frames, and min_confidence."""
        self.ratio_threshold = ratio_threshold
        self.confirm_frames = confirm_frames
        self.min_confidence = min_confidence

    def detect(self, track_history):
        """Return FALL_ALERT-style result from one track history."""
        recent_history = self._get_recent_history(track_history)
        if not recent_history:
            return None

        fall_frames = [entry for entry in recent_history if self._is_fall_like(entry)]
        latest = recent_history[-1]
        duration_frames = len(fall_frames)
        is_fall = duration_frames >= self.confirm_frames
        confidence = self._calculate_confidence(duration_frames)

        return {
            "type": "FALL_ALERT",
            "trackId": latest.get("trackId"),
            "isFall": is_fall,
            "confidence": confidence,
            "durationFrames": duration_frames,
            "level": self._get_level(is_fall, confidence),
        }

    def _get_recent_history(self, track_history):
        """Keep only the recent frames needed for fall confirmation."""
        if not track_history:
            return []
        return list(track_history)[-self.confirm_frames :]

    def _is_fall_like(self, entry):
        """Return whether one bbox looks horizontally fallen."""
        bbox = entry.get("bbox")
        if not bbox:
            return False

        width, height = self._get_bbox_size(bbox)
        if height <= 0:
            return False

        return width / height >= self.ratio_threshold

    def _get_bbox_size(self, bbox):
        """Extract bbox width and height from dict or tuple."""
        if isinstance(bbox, dict):
            width = bbox.get("x2", 0) - bbox.get("x1", 0)
            height = bbox.get("y2", 0) - bbox.get("y1", 0)
            return width, height

        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            return x2 - x1, y2 - y1

        return 0, 0

    def _calculate_confidence(self, duration_frames):
        """Calculate confidence from confirmed fall-like frame count."""
        if self.confirm_frames <= 0:
            return 0.0
        confidence = duration_frames / self.confirm_frames
        return round(min(1.0, max(0.0, confidence)), 2)

    def _get_level(self, is_fall, confidence):
        """Map fall state and confidence to alert level."""
        if is_fall and confidence >= self.min_confidence:
            return "high"
        if confidence > 0:
            return "medium"
        return "low"
