from dataclasses import dataclass
import base64
import json
from pathlib import Path
from urllib.parse import urljoin


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass
class FaceRecord:
    """Store one employee face embedding and identity metadata."""

    employee_id: object
    employee_no: str | None
    name: str | None
    feature: object
    source: str | None = None


class FaceRecognitionService:
    """Load employee face library and recognize faces with InsightFace."""

    def __init__(
        self,
        model_name: str = "buffalo_l",
        model_root: str | Path | None = None,
        similarity_threshold: float = 0.45,
        det_size: tuple[int, int] = (640, 640),
        provider: str = "auto",
        library_path: str | Path | None = None,
        image_dir: str | Path | None = None,
        image_base_url: str = "",
    ):
        """Initialize InsightFace settings and face-library paths."""
        self.model_name = model_name
        self.model_root = Path(model_root) if model_root else None
        self.similarity_threshold = similarity_threshold
        self.det_size = det_size
        self.provider = provider
        self.library_path = Path(library_path) if library_path else None
        self.image_dir = Path(image_dir) if image_dir else None
        self.image_base_url = image_base_url
        self.app = None
        self.providers = []
        self.face_records: list[FaceRecord] = []
        self.load_errors: list[str] = []

    def load_face_library(
        self,
        records: list[dict] | None = None,
        employee_items: list[dict] | None = None,
        library_path: str | Path | None = None,
        image_dir: str | Path | None = None,
        image_base_url: str | None = None,
    ):
        """Load face records from direct records, employee items, JSON, or image directory."""
        self.face_records = []
        self.load_errors = []
        image_base_url = self.image_base_url if image_base_url is None else image_base_url

        if records:
            self._load_record_items(records, image_base_url=image_base_url)

        if employee_items:
            self._load_record_items(employee_items, image_base_url=image_base_url)

        selected_library_path = Path(library_path) if library_path else self.library_path
        if selected_library_path and selected_library_path.exists():
            self._load_json_library(selected_library_path, image_base_url=image_base_url)

        selected_image_dir = Path(image_dir) if image_dir else self.image_dir
        if selected_image_dir and selected_image_dir.exists():
            self._load_image_directory(selected_image_dir)

        return {
            "count": len(self.face_records),
            "errors": self.load_errors,
            "threshold": self.similarity_threshold,
            "modelName": self.model_name,
        }

    def recognize(self, frame, person_detections: list[dict] | None = None, frame_id: str | None = None):
        """Recognize faces in frame and bind results to person track IDs when provided."""
        faces = self._detect_faces(frame)
        if not faces:
            return []

        assignments = self._assign_faces(faces, person_detections or [])
        results = []
        for index, (face, person_detection) in enumerate(assignments, start=1):
            track_id = None
            if person_detection:
                track_id = person_detection.get("trackId")
            elif not person_detections:
                track_id = f"face-{index}"

            if person_detections and not track_id:
                continue

            match, similarity = self._match(self._face_embedding(face))
            face_box = _format_bbox(face.bbox)
            if match and similarity >= self.similarity_threshold:
                result = {
                    "type": "FACE_RESULT",
                    "trackId": track_id,
                    "employeeId": match.employee_id,
                    "employeeNo": match.employee_no,
                    "name": match.name,
                    "matched": True,
                    "similarity": round(float(similarity), 4),
                    "faceBox": face_box,
                }
            else:
                result = {
                    "type": "FACE_RESULT",
                    "trackId": track_id,
                    "employeeId": None,
                    "matched": False,
                    "label": "unknown",
                    "similarity": round(float(similarity), 4),
                    "faceBox": face_box,
                }

            if frame_id is not None:
                result["frameId"] = frame_id
            results.append(result)

        return results

    def extract_feature(self, image):
        """Extract one normalized face feature from an image path or frame."""
        frame = self._load_image(image) if isinstance(image, (str, Path)) else image
        faces = self._detect_faces(frame)
        if not faces:
            raise ValueError("No face detected in image.")
        return self._face_embedding(faces[0])

    def status(self):
        """Return model, provider, threshold, and loaded face-library status."""
        return {
            "loadedFaces": len(self.face_records),
            "modelLoaded": self.app is not None,
            "modelName": self.model_name,
            "providers": self.providers,
            "threshold": self.similarity_threshold,
            "errors": self.load_errors,
        }

    def _load_json_library(self, library_path: Path, image_base_url: str):
        """Load face records from one JSON library file."""
        try:
            with library_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            self.load_errors.append(f"{library_path}: {exc}")
            return

        items = _extract_items(payload)
        self._load_record_items(
            items,
            image_base_url=image_base_url,
            base_dir=library_path.parent,
        )

    def _load_image_directory(self, image_dir: Path):
        """Load employee face images from a directory tree."""
        metadata = _load_metadata(image_dir / "metadata.json")
        items = []
        for image_path in image_dir.rglob("*"):
            if not image_path.is_file() or image_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
                continue

            key = image_path.parent.name if image_path.parent != image_dir else image_path.stem
            item = dict(metadata.get(key) or metadata.get(image_path.stem) or _metadata_from_key(key))
            item["imagePath"] = str(image_path)
            items.append(item)

        self._load_record_items(items, base_dir=image_dir)

    def _load_record_items(
        self,
        items: list[dict],
        image_base_url: str = "",
        base_dir: Path | None = None,
    ):
        """Expand and load a list of employee or face record dictionaries."""
        for item in items:
            for expanded in _expand_record_item(item):
                try:
                    self._load_single_record(expanded, image_base_url=image_base_url, base_dir=base_dir)
                except Exception as exc:
                    identifier = _first(expanded, "employeeId", "employee_id", "employeeNo", "employee_no", default="unknown")
                    self.load_errors.append(f"{identifier}: {exc}")

    def _load_single_record(self, item: dict, image_base_url: str = "", base_dir: Path | None = None):
        """Load one FaceRecord from feature vector or image source."""
        employee_id = _first(item, "employeeId", "employee_id", "id")
        employee_no = _first(item, "employeeNo", "employee_no", "number", "no")
        name = _first(item, "name", "employeeName", "employee_name")
        feature = _first(item, "feature", "featureVector", "feature_vector", "embedding")
        image_source = _first(
            item,
            "imagePath",
            "image_path",
            "imageUrl",
            "image_url",
            "imageBase64",
            "image_base64",
            "faceImage",
            "face_image",
            "faceImageUrl",
            "face_image_url",
            "facePhoto",
            "face_photo",
            "photoUrl",
            "photo_url",
            "photo",
            "avatar",
            "avatarUrl",
            "avatar_url",
            "filePath",
            "file_path",
            "url",
            "image",
        )

        if feature is not None:
            vector = _normalize_vector(feature)
        elif image_source:
            frame = self._load_image(image_source, image_base_url=image_base_url, base_dir=base_dir)
            vector = self.extract_feature(frame)
        else:
            return

        self.face_records.append(
            FaceRecord(
                employee_id=employee_id,
                employee_no=str(employee_no) if employee_no is not None else None,
                name=str(name) if name is not None else None,
                feature=vector,
                source=str(image_source) if image_source else "featureVector",
            )
        )

    def _detect_faces(self, frame):
        """Run InsightFace detection on one frame and sort faces by area."""
        app = self._load_model()
        faces = app.get(frame)
        return sorted(faces, key=lambda face: _bbox_area(face.bbox), reverse=True)

    def _load_model(self):
        """Lazy-load InsightFace FaceAnalysis model with selected providers."""
        if self.app is not None:
            return self.app

        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise RuntimeError(
                "insightface is required for face recognition. Run `pip install -r requirements.txt` in ai-service."
            ) from exc

        providers, ctx_id = _resolve_providers(self.provider)
        self.providers = providers
        kwargs = {"name": self.model_name, "providers": providers}
        if self.model_root:
            self.model_root.mkdir(parents=True, exist_ok=True)
            kwargs["root"] = str(self.model_root)

        try:
            self.app = FaceAnalysis(**kwargs)
            self.app.prepare(ctx_id=ctx_id, det_size=self.det_size)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to load InsightFace model '{self.model_name}'. "
                f"Check model files under {self.model_root or 'default insightface root'} "
                "or allow the first-run model download."
            ) from exc

        return self.app

    def _load_image(self, image_source, image_base_url: str = "", base_dir: Path | None = None):
        """Load image from frame, path, base64 data, or URL."""
        import cv2
        import numpy as np
        import requests

        if not isinstance(image_source, (str, Path)):
            return image_source

        source = str(image_source)
        if _is_data_url(source) and "," in source:
            source = source.split(",", maxsplit=1)[1]

        if _looks_like_base64(source):
            buffer = np.frombuffer(base64.b64decode(source), dtype=np.uint8)
            frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError("Unable to decode base64 image.")
            return frame

        if _is_remote_url(source) or _should_use_base_url(source, image_base_url, base_dir):
            url = source if _is_remote_url(source) else urljoin(image_base_url, source)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            buffer = np.frombuffer(response.content, dtype=np.uint8)
            frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            if frame is None:
                raise ValueError(f"Unable to decode image URL: {url}")
            return frame

        path = Path(source)
        if not path.is_absolute() and base_dir:
            path = base_dir / path
        frame = cv2.imread(str(path))
        if frame is None:
            raise ValueError(f"Unable to read image: {path}")
        return frame

    def _face_embedding(self, face):
        """Return normalized embedding from an InsightFace face object."""
        feature = getattr(face, "normed_embedding", None)
        if feature is None:
            feature = getattr(face, "embedding", None)
        return _normalize_vector(feature)

    def _match(self, feature):
        """Find the most similar loaded FaceRecord for one feature."""
        if not self.face_records:
            return None, 0.0

        import numpy as np

        best_record = None
        best_similarity = -1.0
        for record in self.face_records:
            similarity = float(np.dot(feature, record.feature))
            if similarity > best_similarity:
                best_similarity = similarity
                best_record = record

        return best_record, max(0.0, best_similarity)

    def _assign_faces(self, faces, person_detections: list[dict]):
        """Assign detected faces to person detections by containment and IoU."""
        if not person_detections:
            return [(face, None) for face in faces]

        assignments = []
        used_tracks = set()
        for face in faces:
            face_box = _bbox_tuple(face.bbox)
            center = ((face_box[0] + face_box[2]) / 2, (face_box[1] + face_box[3]) / 2)
            best_detection = None
            best_score = 0.0

            for detection in person_detections:
                track_id = detection.get("trackId")
                if track_id in used_tracks:
                    continue

                person_box = _detection_bbox(detection)
                if person_box is None:
                    continue

                score = _box_iou(face_box, person_box)
                if _point_inside(center, person_box):
                    score += 1.0

                if score > best_score:
                    best_score = score
                    best_detection = detection

            if best_detection is not None:
                used_tracks.add(best_detection.get("trackId"))
                assignments.append((face, best_detection))

        return assignments


def _resolve_providers(provider: str):
    """Resolve InsightFace ONNXRuntime providers and ctx_id from provider option."""
    try:
        import onnxruntime as ort

        available = set(ort.get_available_providers())
    except Exception:
        available = {"CPUExecutionProvider"}

    if provider == "cpu":
        return ["CPUExecutionProvider"], -1

    wants_cuda = provider in {"auto", "cuda", "gpu"}
    if wants_cuda and "CUDAExecutionProvider" in available:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"], 0

    return ["CPUExecutionProvider"], -1


def _extract_items(payload):
    """Extract item list from common face-library response shapes."""
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("items", "records", "faces", "employees", "results"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def _expand_record_item(item):
    """Expand employee records containing nested face/image arrays."""
    if not isinstance(item, dict):
        return []

    employee = item.get("employee") if isinstance(item.get("employee"), dict) else {}
    base = dict(employee)
    base.update({key: value for key, value in item.items() if key != "employee"})
    _preserve_employee_identity(base)

    nested_keys = (
        "faceFeatures",
        "face_features",
        "faceFeatureList",
        "face_feature_list",
        "faces",
        "faceImages",
        "face_images",
        "facePhotos",
        "face_photos",
        "photos",
        "images",
        "imagePaths",
        "image_paths",
    )
    expanded = []
    for key in nested_keys:
        value = item.get(key)
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict):
                    merged = dict(base)
                    if "id" in entry and "faceFeatureId" not in entry and "face_feature_id" not in entry:
                        merged["faceFeatureId"] = entry["id"]
                    merged.update(entry)
                    expanded.append(merged)
                else:
                    merged = dict(base)
                    merged["imagePath"] = entry
                    expanded.append(merged)
        elif isinstance(value, dict):
            merged = dict(base)
            if "id" in value and "faceFeatureId" not in value and "face_feature_id" not in value:
                merged["faceFeatureId"] = value["id"]
            merged.update(value)
            expanded.append(merged)

    return expanded or [base]


def _preserve_employee_identity(item):
    """Keep parent employee id as employeeId before merging nested face feature id."""
    if "id" in item and "employeeId" not in item and "employee_id" not in item:
        item["employeeId"] = item["id"]


def _load_metadata(path: Path):
    """Load optional metadata.json for local employee face folders."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}

    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return {str(_first(item, "employeeId", "employeeNo", "name", default=index)): item for index, item in enumerate(payload["items"])}
    return payload if isinstance(payload, dict) else {}


def _metadata_from_key(key: str):
    """Infer employee metadata from folder/file key like '1_E001_Name'."""
    parts = [part for part in key.split("_") if part]
    data = {}
    if parts:
        data["employeeId"] = int(parts[0]) if parts[0].isdigit() else parts[0]
    if len(parts) >= 2:
        data["employeeNo"] = parts[1]
    if len(parts) >= 3:
        data["name"] = "_".join(parts[2:])
    return data


def _first(mapping, *keys, default=None):
    """Return first non-empty mapping value among keys."""
    for key in keys:
        value = mapping.get(key) if isinstance(mapping, dict) else None
        if value not in (None, ""):
            return value
    return default


def _normalize_vector(feature):
    """Convert feature list/string/array into unit-length float32 vector."""
    import numpy as np

    if isinstance(feature, str):
        feature = json.loads(feature)

    vector = np.asarray(feature, dtype="float32")
    norm = float(np.linalg.norm(vector))
    if norm <= 0:
        raise ValueError("Face feature vector norm is zero.")
    return vector / norm


def _looks_like_base64(value: str):
    """Heuristically detect base64 image content."""
    if len(value) < 64:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
    return all(char in allowed for char in value[:128])


def _is_data_url(value: str):
    """Return whether value is a data URL."""
    return value.startswith("data:image") or value.startswith("data:application/octet-stream")


def _is_remote_url(value: str):
    """Return whether value is an HTTP or HTTPS URL."""
    return value.startswith(("http://", "https://"))


def _should_use_base_url(source: str, image_base_url: str, base_dir: Path | None):
    """Decide whether a relative image source should use image_base_url."""
    if not image_base_url:
        return False

    path = Path(source)
    if path.is_absolute():
        return False

    if base_dir and (base_dir / path).exists():
        return False

    return True


def _bbox_tuple(bbox):
    """Convert bbox-like object to xyxy float tuple."""
    values = [float(value) for value in bbox[:4]]
    return values[0], values[1], values[2], values[3]


def _format_bbox(bbox):
    """Format bbox as rounded JSON object."""
    x1, y1, x2, y2 = _bbox_tuple(bbox)
    return {
        "x1": round(x1, 2),
        "y1": round(y1, 2),
        "x2": round(x2, 2),
        "y2": round(y2, 2),
    }


def _bbox_area(bbox):
    """Calculate bbox area from xyxy coordinates."""
    x1, y1, x2, y2 = _bbox_tuple(bbox)
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _detection_bbox(detection):
    """Extract xyxy bbox tuple from a detection dict."""
    bbox = detection.get("bbox") if isinstance(detection, dict) else None
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


def _point_inside(point, bbox):
    """Return whether point is inside bbox."""
    x, y = point
    x1, y1, x2, y2 = bbox
    return x1 <= x <= x2 and y1 <= y <= y2


def _box_iou(box_a, box_b):
    """Calculate IoU for two xyxy boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union_area = area_a + area_b - inter_area
    return inter_area / union_area if union_area > 0 else 0.0
