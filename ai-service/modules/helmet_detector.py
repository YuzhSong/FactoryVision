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


class HelmetDetector:
    """Detect helmet status with a PPE YOLO model and format helmet warnings."""

    def __init__(
        self,
        model_path: str | None = None,
        confidence_threshold: float = 0.6,
        detection_confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: str = "auto",
        image_size: int = 640,
        half_precision: str | bool = "auto",
        cudnn_benchmark: bool = True,
    ):
        """Initialize helmet detector with model path, thresholds, and runtime options."""
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.detection_confidence_threshold = detection_confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.image_size = image_size
        self.half_precision = half_precision
        self.cudnn_benchmark = cudnn_benchmark
        self.model = None
        self.class_names = {}
        self.helmet_class_ids = set()
        self.no_helmet_class_ids = set()

    def load_model(self):
        """Lazy-load the helmet YOLO model and cache class IDs."""
        if self.model is not None:
            return self.model

        if not self.model_path:
            raise RuntimeError("HELMET_MODEL_PATH is not configured.")

        model_path = Path(self.model_path)
        if not model_path.exists():
            raise RuntimeError(
                f"Helmet model not found: {model_path}. "
                "Download Hexmon/vyra-yolo-ppe-detection best.pt as models/helmet/helmet.pt."
            )

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
        self.helmet_class_ids = _class_ids_for_status(self.class_names, "helmet")
        self.no_helmet_class_ids = _class_ids_for_status(self.class_names, "no_helmet")
        return self.model

    def detect(self, frame, person_detections=None, frame_id: str | None = None):
        """Detect helmet/no-helmet boxes and attach track IDs when person detections are provided."""
        if not self.model_path:
            return []

        model = self.load_model()
        target_classes = sorted(self.helmet_class_ids | self.no_helmet_class_ids) or None
        predictions = model.predict(
            source=frame,
            conf=self.detection_confidence_threshold,
            iou=self.iou_threshold,
            classes=target_classes,
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
            helmet_status = _status_from_class_name(class_name)
            if helmet_status is None:
                continue

            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            confidence = float(box.conf[0].item())
            track_id = _match_person_track((x1, y1, x2, y2), person_detections or [])
            detection = {
                "type": "HELMET_DETECTION",
                "trackId": track_id,
                "helmetStatus": helmet_status,
                "helmetConfidence": round(confidence, 4),
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

        return detections

    def format_warning(self, track_id, helmet_status, confidence, level=None):
        """Format HELMET_WARNING when status is no_helmet and confidence is high enough."""
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
        """Map helmet confidence to warning level."""
        if confidence >= 0.85:
            return "high"
        if confidence >= self.confidence_threshold:
            return "medium"
        return "low"


def _class_ids_for_status(class_names, status):
    """Return model class IDs matching helmet or no-helmet status."""
    return {
        int(class_id)
        for class_id, class_name in class_names.items()
        if _status_from_class_name(str(class_name)) == status
    }


def _status_from_class_name(class_name):
    """Normalize PPE model class names to helmet/no_helmet status."""
    normalized = class_name.strip().lower().replace("_", "-")
    if any(keyword in normalized for keyword in NO_HELMET_KEYWORDS):
        return "no_helmet"
    if any(keyword in normalized for keyword in HELMET_KEYWORDS):
        return "helmet"
    return None


def _match_person_track(helmet_box, person_detections):
    """Find the person track whose bbox contains the helmet box center."""
    hx1, hy1, hx2, hy2 = helmet_box
    center_x = (hx1 + hx2) / 2
    center_y = (hy1 + hy2) / 2
    best_track_id = None
    best_score = 0.0

    for person in person_detections:
        bbox = _person_bbox(person.get("bbox"))
        if bbox is None:
            continue

        px1, py1, px2, py2 = bbox
        if not (px1 <= center_x <= px2 and py1 <= center_y <= py2):
            continue

        person_area = max(1.0, (px2 - px1) * (py2 - py1))
        helmet_area = max(0.0, hx2 - hx1) * max(0.0, hy2 - hy1)
        head_bonus = 1.0 if center_y <= py1 + (py2 - py1) * 0.55 else 0.5
        score = head_bonus + helmet_area / person_area
        if score > best_score:
            best_score = score
            best_track_id = person.get("trackId")

    return best_track_id


def _person_bbox(bbox):
    """Convert person bbox dict/list to xyxy tuple."""
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
