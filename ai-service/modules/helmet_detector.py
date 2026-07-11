from pathlib import Path

from .person_detector import (
    _configure_cuda_runtime,
    _ensure_ultralytics_config_dir,
    _resolve_device,
    _resolve_half_precision,
    _resolve_model_path,
)


HELMET_KEYWORDS = ("hardhat", "helmet")
NO_HELMET_KEYWORDS = ("no-hardhat", "no_hardhat", "no hardhat", "no-helmet", "no_helmet", "no helmet")
OPEN_SOURCE_PROVIDER = "opensource"
SELF_TRAINED_PROVIDER = "self_trained"


class HelmetDetector:
    """Detect helmet status and format helmet warnings for both model providers."""

    def __init__(
        self,
        model_path: str | None = None,
        provider: str = OPEN_SOURCE_PROVIDER,
        confidence_threshold: float = 0.6,
        detection_confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: str = "auto",
        image_size: int = 640,
        half_precision: str | bool = "auto",
        cudnn_benchmark: bool = True,
        match_upper_ratio: float = 0.65,
        class_ids: tuple[int, ...] = (1, 2),
        helmet_class_id: int = 1,
        no_helmet_class_id: int = 2,
    ):
        self.model_path = model_path
        self.provider = _normalize_provider(provider)
        self.confidence_threshold = confidence_threshold
        self.detection_confidence_threshold = detection_confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.image_size = image_size
        self.half_precision = half_precision
        self.cudnn_benchmark = cudnn_benchmark
        self.match_upper_ratio = float(match_upper_ratio)
        self.class_ids = tuple(int(value) for value in class_ids or ())
        self.helmet_class_id = int(helmet_class_id)
        self.no_helmet_class_id = int(no_helmet_class_id)
        self.model = None
        self.class_names = {}
        self.helmet_class_ids = set()
        self.no_helmet_class_ids = set()

    def load_model(self):
        """Lazy-load configured helmet model and cache resolved class IDs."""
        if self.model is not None:
            return self.model

        if not self.model_path:
            raise RuntimeError("HELMET_MODEL_PATH is not configured.")

        model_path = Path(self.model_path)
        if not model_path.exists():
            raise RuntimeError(f"Helmet model not found: {model_path}.")

        _ensure_ultralytics_config_dir()

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Run `pip install -r requirements.txt` in ai-service."
            ) from exc

        self.device = _resolve_device(self.device)
        _configure_cuda_runtime(self.device, self.cudnn_benchmark)
        self.model = YOLO(_resolve_model_path(str(model_path)))
        self.class_names = dict(getattr(self.model, "names", {}) or {})
        self._refresh_class_id_cache()
        return self.model

    def detect(self, frame, person_detections=None, camera_id=None, timestamp=None, frame_id: str | None = None):
        """Detect helmet/no-helmet boxes and optionally match them onto person tracks."""
        del camera_id, timestamp

        if not self.model_path:
            return []

        model = self.load_model()
        predictions = model.predict(
            source=frame,
            conf=self.detection_confidence_threshold,
            iou=self.iou_threshold,
            classes=self._target_classes(),
            device=self.device,
            imgsz=self.image_size,
            half=_resolve_half_precision(self.half_precision, self.device),
            verbose=False,
        )

        detections = []
        if not predictions:
            return detections

        for box in predictions[0].boxes:
            class_id = int(box.cls[0].item())
            class_name = str(self.class_names.get(class_id, class_id))
            helmet_status = self._resolve_status(class_id, class_name)
            if helmet_status is None:
                continue

            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            detection = {
                "type": "HELMET_DETECTION",
                "helmetStatus": helmet_status,
                "helmetConfidence": round(float(box.conf[0].item()), 4),
                "classId": class_id,
                "className": class_name,
                "bbox": {
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "x2": round(x2, 2),
                    "y2": round(y2, 2),
                },
            }
            if frame_id is not None:
                detection["frameId"] = frame_id
            detections.append(detection)

        if not person_detections:
            return detections

        return self._match_to_people(detections, person_detections, frame_id=frame_id)

    def annotate_person_detections(self, person_detections, helmet_detections):
        """Copy matched helmet status fields onto person detection results."""
        by_track_id = {
            detection.get("trackId"): detection
            for detection in helmet_detections or []
            if detection.get("trackId")
        }
        for person in person_detections or []:
            helmet = by_track_id.get(person.get("trackId"))
            if not helmet:
                continue
            person["helmetStatus"] = helmet.get("helmetStatus")
            person["helmetConfidence"] = helmet.get("helmetConfidence", helmet.get("confidence"))
            if helmet.get("className") is not None:
                person["helmetClassName"] = helmet.get("className")
        return person_detections

    def format_warning(self, track_id, helmet_status, confidence, level=None, bbox=None):
        """Format HELMET_WARNING when status is no_helmet and confidence is high enough."""
        if helmet_status != "no_helmet":
            return None

        confidence = float(confidence)
        if confidence < self.confidence_threshold:
            return None

        warning = {
            "type": "HELMET_WARNING",
            "helmetStatus": helmet_status,
            "confidence": confidence,
            "level": level or self._get_level(confidence),
        }
        if track_id is not None:
            warning["trackId"] = str(track_id)
        if bbox:
            warning["bbox"] = bbox
        return warning

    def _refresh_class_id_cache(self):
        if self.provider == SELF_TRAINED_PROVIDER:
            self.helmet_class_ids = {self.helmet_class_id}
            self.no_helmet_class_ids = {self.no_helmet_class_id}
            return

        self.helmet_class_ids = _class_ids_for_status(self.class_names, "helmet")
        self.no_helmet_class_ids = _class_ids_for_status(self.class_names, "no_helmet")

    def _target_classes(self):
        if self.provider == SELF_TRAINED_PROVIDER:
            return sorted(set(self.class_ids)) or None

        target_classes = sorted(self.helmet_class_ids | self.no_helmet_class_ids)
        return target_classes or None

    def _resolve_status(self, class_id, class_name):
        if self.provider == SELF_TRAINED_PROVIDER:
            if class_id == self.helmet_class_id:
                return "helmet"
            if class_id == self.no_helmet_class_id:
                return "no_helmet"
            return None

        return _status_from_class_name(class_name)

    def _get_level(self, confidence):
        if confidence >= 0.85:
            return "high"
        if confidence >= self.confidence_threshold:
            return "medium"
        return "low"

    def _match_to_people(self, helmet_results, person_detections, frame_id=None):
        """Attach each best helmet result to a person using the upper-body region first."""
        matched = []
        used_indexes = set()
        for person in person_detections or []:
            person_bbox = _person_bbox(person.get("bbox"))
            if person_bbox is None:
                continue

            best_index = None
            best_score = 0.0
            for index, helmet in enumerate(helmet_results):
                if index in used_indexes:
                    continue
                helmet_bbox = _person_bbox(helmet.get("bbox"))
                if helmet_bbox is None:
                    continue

                score = self._person_match_score(person_bbox, helmet_bbox)
                if score > best_score:
                    best_score = score
                    best_index = index

            if best_index is None or best_score <= 0:
                continue

            used_indexes.add(best_index)
            helmet = dict(helmet_results[best_index])
            helmet["trackId"] = person.get("trackId")
            if frame_id is not None:
                helmet["frameId"] = frame_id
            matched.append(helmet)

        for index, helmet in enumerate(helmet_results):
            if index not in used_indexes:
                matched.append(helmet)
        return matched

    def _person_match_score(self, person_bbox, helmet_bbox):
        px1, py1, px2, py2 = person_bbox
        hx1, hy1, hx2, hy2 = helmet_bbox
        center_x = (hx1 + hx2) / 2
        center_y = (hy1 + hy2) / 2
        upper_y2 = py1 + max(0.0, py2 - py1) * self.match_upper_ratio

        if px1 <= center_x <= px2 and py1 <= center_y <= upper_y2:
            return 1.0 + _iou(person_bbox, helmet_bbox)
        return _iou(person_bbox, helmet_bbox)


def _normalize_provider(provider):
    normalized = str(provider or OPEN_SOURCE_PROVIDER).strip().lower()
    if normalized in {"self-trained", "selftrained"}:
        return SELF_TRAINED_PROVIDER
    if normalized not in {OPEN_SOURCE_PROVIDER, SELF_TRAINED_PROVIDER}:
        return OPEN_SOURCE_PROVIDER
    return normalized


def _class_ids_for_status(class_names, status):
    return {
        int(class_id)
        for class_id, class_name in class_names.items()
        if _status_from_class_name(str(class_name)) == status
    }


def _status_from_class_name(class_name):
    normalized = str(class_name).strip().lower().replace("_", "-")
    if any(keyword in normalized for keyword in NO_HELMET_KEYWORDS):
        return "no_helmet"
    if any(keyword in normalized for keyword in HELMET_KEYWORDS):
        return "helmet"
    return None


def _person_bbox(bbox):
    if isinstance(bbox, dict):
        return (
            float(bbox.get("x1", 0)),
            float(bbox.get("y1", 0)),
            float(bbox.get("x2", 0)),
            float(bbox.get("y2", 0)),
        )
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        return tuple(float(value) for value in bbox)
    return None


def _iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    intersection_x1 = max(ax1, bx1)
    intersection_y1 = max(ay1, by1)
    intersection_x2 = min(ax2, bx2)
    intersection_y2 = min(ay2, by2)
    intersection_area = max(0.0, intersection_x2 - intersection_x1) * max(0.0, intersection_y2 - intersection_y1)
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - intersection_area
    if union_area <= 0:
        return 0.0
    return intersection_area / union_area
