from pathlib import Path

import cv2


class PersonDetector:
    PERSON_CLASS_ID = 0

    def __init__(self, confidence_threshold: float = 0.5, model_path=None):
        self.confidence_threshold = confidence_threshold
        self.model_path = Path(model_path) if model_path else self._default_model_path()
        self.model = None
        self.backend = None

    def load_model(self):
        if self.model_path.exists():
            try:
                from ultralytics import YOLO

                self.model = YOLO(str(self.model_path))
                self.backend = "yolo"
                return self
            except Exception:
                self.model = None
                self.backend = None

        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.model = hog
        self.backend = "opencv-hog"
        return self

    def detect(self, frame):
        if frame is None:
            return []
        if self.model is None:
            self.load_model()

        if self.backend == "yolo":
            return self._detect_with_yolo(frame)
        return self._detect_with_hog(frame)

    def draw_detections(self, frame, detections):
        annotated_frame = frame.copy()
        for detection in detections or []:
            bbox = detection.get("bbox", {})
            x1 = int(bbox.get("x1", 0))
            y1 = int(bbox.get("y1", 0))
            x2 = int(bbox.get("x2", 0))
            y2 = int(bbox.get("y2", 0))
            confidence = detection.get("confidence", 0)
            backend = detection.get("backend", self.backend or "detector")
            label = f"person {confidence:.2f}"

            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            self._draw_label(annotated_frame, f"{label} {backend}", x1, y1)

        return annotated_frame

    def _detect_with_yolo(self, frame):
        results = self.model.predict(frame, conf=self.confidence_threshold, classes=[self.PERSON_CLASS_ID], verbose=False)
        detections = []
        if not results:
            return detections

        boxes = getattr(results[0], "boxes", None)
        if boxes is None:
            return detections

        for index, box in enumerate(boxes, start=1):
            xyxy = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            detection = self.format_detection(
                track_id=f"person-{index}",
                bbox=[int(value) for value in xyxy],
                confidence=round(confidence, 4),
                extra={"backend": "yolo", "classId": self.PERSON_CLASS_ID, "className": "person"},
            )
            if detection:
                detections.append(detection)

        return detections

    def _detect_with_hog(self, frame):
        boxes, weights = self.model.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )

        detections = []
        for index, (box, weight) in enumerate(zip(boxes, weights), start=1):
            confidence = float(weight)
            if confidence < self.confidence_threshold:
                continue

            x, y, width, height = [int(value) for value in box]
            detection = self.format_detection(
                track_id=f"person-{index}",
                bbox=[x, y, x + width, y + height],
                confidence=round(confidence, 4),
                extra={"backend": "opencv-hog", "className": "person"},
            )
            if detection:
                detections.append(detection)

        return detections

    def _draw_label(self, frame, label, x, y):
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        thickness = 1
        text_size, baseline = cv2.getTextSize(label, font, font_scale, thickness)
        text_width, text_height = text_size
        top = max(y - text_height - baseline - 6, 0)

        cv2.rectangle(frame, (x, top), (x + text_width + 8, top + text_height + baseline + 6), (0, 255, 0), -1)
        cv2.putText(frame, label, (x + 4, top + text_height + 2), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)

    def format_detection(self, track_id, bbox, confidence, extra=None):
        x1, y1, x2, y2 = self._normalize_bbox(bbox)
        if confidence < self.confidence_threshold:
            return None

        result = {
            "type": "PERSON_DETECTION",
            "trackId": str(track_id),
            "bbox": {
                "x1": int(x1),
                "y1": int(y1),
                "x2": int(x2),
                "y2": int(y2),
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

    def _default_model_path(self):
        return Path(__file__).resolve().parents[1] / "models" / "yolov8n.pt"
