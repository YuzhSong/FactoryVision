from dataclasses import dataclass
from pathlib import Path


PERSON_CLASS_ID = 0


@dataclass
class _Track:
    track_id: str
    bbox: tuple[float, float, float, float]
    missed_frames: int = 0


class PersonDetector:
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
        self._tracks = []
        self._next_track_number = 1

    def _assign_tracks(self, boxes):
        for track in self._tracks:
            track.missed_frames += 1

        assignments = []
        used_track_indexes = set()

        for box in boxes:
            bbox = box[:4]
            best_index = None
            best_iou = 0.0

            for index, track in enumerate(self._tracks):
                if index in used_track_indexes:
                    continue
                overlap = _iou(bbox, track.bbox)
                if overlap > best_iou:
                    best_iou = overlap
                    best_index = index

            if best_index is not None and best_iou >= self.track_iou_threshold:
                track = self._tracks[best_index]
                track.bbox = bbox
                track.missed_frames = 0
                used_track_indexes.add(best_index)
                assignments.append((track.track_id, box))
                continue

            track = _Track(track_id=f"t-{self._next_track_number}", bbox=bbox)
            self._next_track_number += 1
            self._tracks.append(track)
            used_track_indexes.add(len(self._tracks) - 1)
            assignments.append((track.track_id, box))

        self._tracks = [
            track
            for track in self._tracks
            if track.missed_frames <= self.max_missed_frames
        ]
        return assignments


def _iou(box_a, box_b):
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


def _ensure_ultralytics_config_dir():
    from config import Config

    Config.ULTRALYTICS_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_model_path(model_path: str):
    path = Path(model_path)
    if path.exists():
        return str(path)

    if path.name in {"yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolo11n.pt", "yolo11s.pt"}:
        return path.name

    return model_path


def _resolve_device(device: str):
    if device != "auto":
        return device

    try:
        import torch
    except ImportError:
        return "cpu"

    return "cuda:0" if torch.cuda.is_available() else "cpu"


def _resolve_half_precision(value, device: str):
    if isinstance(value, bool):
        return value and device.startswith("cuda")

    normalized = str(value).strip().lower()
    if normalized == "auto":
        return device.startswith("cuda")
    return normalized in {"1", "true", "yes", "y", "on"} and device.startswith("cuda")


def _configure_cuda_runtime(device: str, cudnn_benchmark: bool):
    if not device.startswith("cuda"):
        return

    try:
        import torch

        torch.backends.cudnn.benchmark = bool(cudnn_benchmark)
    except Exception:
        return
