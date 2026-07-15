from dataclasses import dataclass
from pathlib import Path


PERSON_CLASS_ID = 0


@dataclass
class _Track:
    """Store one lightweight IoU track with bbox and missed-frame count."""

    track_id: str
    bbox: tuple[float, float, float, float]
    missed_frames: int = 0


class PersonDetector:
    """Detect person boxes with YOLO and assign lightweight track IDs."""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        device: str = "cpu",
        image_size: int = 640,
        half_precision: str | bool = "auto",
        cudnn_benchmark: bool = True,
        track_iou_threshold: float = 0.3,
        max_missed_frames: int = 15,
    ):
        """Initialize YOLO detector with model, thresholds, device, and tracking options."""
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.image_size = image_size
        self.half_precision = half_precision
        self.cudnn_benchmark = cudnn_benchmark
        self.track_iou_threshold = track_iou_threshold
        self.max_missed_frames = max_missed_frames
        self.model = None
        self._tracks: list[_Track] = []
        self._next_track_number = 1

    def load_model(self):
        """Lazy-load the YOLO model and resolve CUDA/CPU runtime settings."""
        if self.model is not None:
            return self.model

        _ensure_ultralytics_config_dir()

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "ultralytics is not installed. Run `pip install -r requirements.txt` in ai-service."
            ) from exc

        self.device = _resolve_device(self.device)
        _configure_cuda_runtime(self.device, self.cudnn_benchmark)
        self.model = YOLO(_resolve_model_path(self.model_path))
        return self.model

    def detect(self, frame, frame_id: str | None = None):
        """Detect persons in one frame and return PERSON_DETECTION results."""
        model = self.load_model()
        predictions = model.predict(
            source=frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            classes=[PERSON_CLASS_ID],
            device=self.device,
            imgsz=self.image_size,
            half=_resolve_half_precision(self.half_precision, self.device),
            verbose=False,
        )

        person_boxes = []
        if predictions:
            boxes = predictions[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                if cls_id != PERSON_CLASS_ID:
                    continue

                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
                confidence = float(box.conf[0].item())
                person_boxes.append((x1, y1, x2, y2, confidence))

        assigned = self._assign_tracks(person_boxes)
        results = []
        for track_id, (x1, y1, x2, y2, confidence) in assigned:
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            result = {
                "type": "PERSON_DETECTION",
                "trackId": track_id,
                "bbox": {
                    "x1": round(x1, 2),
                    "y1": round(y1, 2),
                    "x2": round(x2, 2),
                    "y2": round(y2, 2),
                },
                "centerPoint": {
                    "x": round(center_x, 2),
                    "y": round(center_y, 2),
                },
                "footPoint": {
                    "x": round(center_x, 2),
                    "y": round(y2, 2),
                },
                "confidence": round(confidence, 4),
            }
            if frame_id is not None:
                result["frameId"] = frame_id
            results.append(result)
        return results

    def reset_tracks(self):
        """Clear all tracked person IDs."""
        self._tracks = []
        self._next_track_number = 1

    def _assign_tracks(self, boxes):
        """Assign boxes by IoU, then bridge obvious upright/fallen shape transitions."""
        for track in self._tracks:
            track.missed_frames += 1

        assignments_by_box = {}
        used_track_indexes = set()
        used_box_indexes = set()

        iou_candidates = []
        for box_index, box in enumerate(boxes):
            for track_index, track in enumerate(self._tracks):
                overlap = _iou(box[:4], track.bbox)
                if overlap >= self.track_iou_threshold:
                    iou_candidates.append((overlap, box_index, track_index))

        for _overlap, box_index, track_index in sorted(iou_candidates, reverse=True):
            if box_index in used_box_indexes or track_index in used_track_indexes:
                continue
            _assign_existing_track(
                self._tracks[track_index],
                boxes[box_index],
                box_index,
                track_index,
                assignments_by_box,
                used_box_indexes,
                used_track_indexes,
            )

        transition_candidates = []
        for box_index, box in enumerate(boxes):
            if box_index in used_box_indexes:
                continue
            for track_index, track in enumerate(self._tracks):
                if track_index in used_track_indexes:
                    continue
                distance = _fall_transition_distance(track.bbox, box[:4], track.missed_frames)
                if distance is not None:
                    transition_candidates.append((distance, box_index, track_index))

        for _distance, box_index, track_index in sorted(transition_candidates):
            if box_index in used_box_indexes or track_index in used_track_indexes:
                continue
            _assign_existing_track(
                self._tracks[track_index],
                boxes[box_index],
                box_index,
                track_index,
                assignments_by_box,
                used_box_indexes,
                used_track_indexes,
            )

        for box_index, box in enumerate(boxes):
            if box_index in used_box_indexes:
                continue
            track = _Track(track_id=f"t-{self._next_track_number}", bbox=box[:4])
            self._next_track_number += 1
            self._tracks.append(track)
            assignments_by_box[box_index] = (track.track_id, box)

        self._tracks = [
            track
            for track in self._tracks
            if track.missed_frames <= self.max_missed_frames
        ]
        return [assignments_by_box[index] for index in range(len(boxes))]


def _iou(box_a, box_b):
    """Calculate IoU between two boxes in xyxy format."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    intersection_x1 = max(ax1, bx1)
    intersection_y1 = max(ay1, by1)
    intersection_x2 = min(ax2, bx2)
    intersection_y2 = min(ay2, by2)

    intersection_width = max(0.0, intersection_x2 - intersection_x1)
    intersection_height = max(0.0, intersection_y2 - intersection_y1)
    intersection_area = intersection_width * intersection_height

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - intersection_area

    if union_area <= 0:
        return 0.0
    return intersection_area / union_area


def _assign_existing_track(
    track,
    box,
    box_index,
    track_index,
    assignments_by_box,
    used_box_indexes,
    used_track_indexes,
):
    track.bbox = box[:4]
    track.missed_frames = 0
    assignments_by_box[box_index] = (track.track_id, box)
    used_box_indexes.add(box_index)
    used_track_indexes.add(track_index)


def _fall_transition_distance(previous_bbox, current_bbox, missed_frames):
    """Return normalized distance for an obvious upright-to-horizontal transition."""
    if missed_frames > 3:
        return None

    previous = _valid_bbox(previous_bbox)
    current = _valid_bbox(current_bbox)
    if previous is None or current is None:
        return None

    px1, py1, px2, py2 = previous
    cx1, cy1, cx2, cy2 = current
    previous_width, previous_height = px2 - px1, py2 - py1
    current_width, current_height = cx2 - cx1, cy2 - cy1
    previous_ratio = previous_width / previous_height
    current_ratio = current_width / current_height
    changes_posture = (
        previous_ratio <= 0.8 and current_ratio >= 1.2
    ) or (
        current_ratio <= 0.8 and previous_ratio >= 1.2
    )
    if not changes_posture:
        return None

    horizontal_overlap = min(px2, cx2) - max(px1, cx1)
    vertical_overlap = min(py2, cy2) - max(py1, cy1)
    if horizontal_overlap <= 0 or vertical_overlap <= 0:
        return None

    previous_center = ((px1 + px2) / 2, (py1 + py2) / 2)
    current_center = ((cx1 + cx2) / 2, (cy1 + cy2) / 2)
    center_distance = (
        (current_center[0] - previous_center[0]) ** 2
        + (current_center[1] - previous_center[1]) ** 2
    ) ** 0.5
    scale = max(previous_height, current_height, 1.0)
    normalized_distance = center_distance / scale
    return normalized_distance if normalized_distance <= 0.75 else None


def _valid_bbox(bbox):
    if not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
        return None
    try:
        x1, y1, x2, y2 = [float(value) for value in bbox[:4]]
    except (TypeError, ValueError):
        return None
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _ensure_ultralytics_config_dir():
    """Ensure Ultralytics writes settings under ai-service data directory."""
    from ai_config import Config

    Config.ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_model_path(model_path: str):
    """Resolve local model path or known Ultralytics model name."""
    path = Path(model_path)
    if path.exists():
        return str(path)

    if path.name in {"yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolo11n.pt", "yolo11s.pt"}:
        return path.name

    return model_path


def _resolve_device(device: str):
    """Resolve 'auto' device to cuda:0 when torch CUDA is available."""
    if device != "auto":
        return device

    try:
        import torch
    except ImportError:
        return "cpu"

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _resolve_half_precision(value, device: str):
    """Enable half precision only when requested and running on CUDA."""
    if isinstance(value, bool):
        return value and device.startswith("cuda")

    normalized = str(value).strip().lower()
    if normalized == "auto":
        return device.startswith("cuda")
    return normalized in {"1", "true", "yes", "y", "on"} and device.startswith("cuda")


def _configure_cuda_runtime(device: str, cudnn_benchmark: bool):
    """Enable CUDA runtime optimizations when using a CUDA device."""
    if not device.startswith("cuda"):
        return

    try:
        import torch

        torch.backends.cudnn.benchmark = bool(cudnn_benchmark)
    except Exception:
        return
