class HelmetDetector:
    def __init__(self, confidence_threshold: float = 0.6):
        self.confidence_threshold = confidence_threshold
        self.model = None

    def load_model(self):
        self.model = None
        return self

    def detect(self, frame, person_detections=None):
        return []

    def format_warning(self, track_id, helmet_status, confidence, level=None):
        if helmet_status != "no_helmet":
            return None
        if confidence < self.confidence_threshold:
            return None

        return {
            "type": "HELMET_WARNING",
            "trackId": str(track_id),
            "helmetStatus": helmet_status,
            "confidence": confidence,
            "level": level or self._get_level(confidence),
        }

    def _get_level(self, confidence):
        if confidence >= 0.85:
            return "high"
        if confidence >= self.confidence_threshold:
            return "medium"
        return "low"
