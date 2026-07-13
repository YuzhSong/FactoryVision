from dataclasses import asdict, dataclass


QUALITY_WARNING = "No verified anti-spoofing model is configured; RGB results are image-quality heuristics only."


@dataclass
class LivenessResult:
    """Separate formal anti-spoofing from non-security image-quality heuristics."""

    available: bool
    passed: bool | None
    score: float | None
    threshold: float | None
    provider: str
    warning: str | None = None
    quality_heuristic_passed: bool | None = None
    quality_heuristic_score: float | None = None

    def to_dict(self):
        return asdict(self)


class LivenessDetector:
    """Expose only verified model results as liveness; RGB is explicitly diagnostic."""

    def __init__(self, enabled=False, provider="rgb_quality_heuristic", threshold=0.70, min_face_size=48, model_path=""):
        self.enabled = bool(enabled)
        self.provider = str(provider or "rgb_quality_heuristic").strip().lower()
        self.threshold = max(0.0, min(1.0, float(threshold)))
        self.min_face_size = max(1, int(min_face_size or 1))
        self.model_path = str(model_path or "")

    def predict(self, face_crop):
        if not self.enabled:
            return LivenessResult(False, None, None, None, self.provider, "Liveness detection is disabled.")
        if self.provider == "onnx":
            return LivenessResult(
                False,
                None,
                None,
                None,
                "onnx",
                "No verified ONNX anti-spoofing model is configured or its output contract is unknown.",
            )
        if self.provider != "rgb_quality_heuristic":
            return LivenessResult(
                False,
                None,
                None,
                None,
                self.provider,
                f"Unsupported liveness provider: {self.provider}.",
            )
        return self._quality_heuristic(face_crop)

    def status(self):
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "available": False,
            "threshold": self.threshold if self.provider == "onnx" else None,
            "minFaceSize": self.min_face_size,
            "modelPath": self.model_path or None,
            "warning": QUALITY_WARNING if self.provider == "rgb_quality_heuristic" else None,
        }

    def _quality_heuristic(self, face_crop):
        if face_crop is None or not hasattr(face_crop, "shape"):
            return LivenessResult(False, None, None, None, "rgb_quality_heuristic", QUALITY_WARNING, False, 0.0)
        height, width = face_crop.shape[:2]
        if min(width, height) < self.min_face_size:
            return LivenessResult(False, None, None, None, "rgb_quality_heuristic", QUALITY_WARNING, False, 0.0)

        import cv2
        import numpy as np

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
        sharpness = min(1.0, float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 120.0)
        texture = min(1.0, float(gray.std()) / 45.0)
        color = min(1.0, float(np.mean(np.std(face_crop, axis=(0, 1)))) / 45.0)
        saturation = min(1.0, float(hsv[:, :, 1].mean()) / 80.0)
        edges = min(1.0, float((cv2.Canny(gray, 60, 160) > 0).mean()) / 0.08)
        score = round(0.30 * sharpness + 0.25 * texture + 0.20 * color + 0.15 * saturation + 0.10 * edges, 4)
        return LivenessResult(False, None, None, None, "rgb_quality_heuristic", QUALITY_WARNING, score >= self.threshold, score)
