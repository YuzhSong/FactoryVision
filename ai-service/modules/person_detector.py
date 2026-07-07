class PersonDetector:
    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold
        self.model = None

    def load_model(self):
        self.model = None
        return self

    def detect(self, frame):
        return []

    def format_detection(self, track_id, bbox, confidence, extra=None):
        x1, y1, x2, y2 = self._normalize_bbox(bbox)
        if confidence < self.confidence_threshold:
            return None

        result = {
            "type": "PERSON_DETECTION",
            "trackId": str(track_id),
            "bbox": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
            },
            "centerPoint": {
                "x": (x1 + x2) / 2,
                "y": (y1 + y2) / 2,
            },
            "footPoint": {
                "x": (x1 + x2) / 2,
                "y": y2,
            },
            "confidence": confidence,
        }

        if extra:
            result.update(extra)

        return result

    def _normalize_bbox(self, bbox):
        if isinstance(bbox, dict):
            return bbox.get("x1", 0), bbox.get("y1", 0), bbox.get("x2", 0), bbox.get("y2", 0)
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return bbox[0], bbox[1], bbox[2], bbox[3]
        raise ValueError("bbox must be a dict or a four-item list/tuple")
