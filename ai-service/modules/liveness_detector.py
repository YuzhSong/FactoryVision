from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class LivenessResult:
    """Serializable RGB liveness decision for one face crop."""

    enabled: bool
    passed: bool
    score: float
    threshold: float
    method: str
    reject_reason: str | None = None
    metrics: dict | None = None

    def to_dict(self):
        data = asdict(self)
        if data["reject_reason"] is None:
            data.pop("reject_reason")
        if not data.get("metrics"):
            data.pop("metrics", None)
        return data


class LivenessDetector:
    """
    Passive RGB face anti-spoofing detector.

    This detector is intentionally model-pluggable. If an ONNX model path is provided,
    model inference is used. Otherwise it falls back to conservative RGB texture
    heuristics that can catch weak printed/screen attacks but are not bank-grade PAD.
    """

    def __init__(
        self,
        enabled: bool = False,
        threshold: float = 0.55,
        min_face_size: int = 48,
        model_path: str | Path | None = None,
        input_size: tuple[int, int] = (80, 80),
    ):
        self.enabled = bool(enabled)
        self.threshold = float(threshold)
        self.min_face_size = max(1, int(min_face_size or 1))
        self.model_path = Path(model_path) if model_path else None
        self.input_size = input_size
        self._session = None
        self._input_name = None

    def predict(self, face_crop):
        """Return liveness decision for one BGR face crop."""
        if not self.enabled:
            return LivenessResult(
                enabled=False,
                passed=True,
                score=1.0,
                threshold=self.threshold,
                method="disabled",
            )

        if face_crop is None or not hasattr(face_crop, "shape"):
            return self._reject("invalid_face_crop", score=0.0, method="rgb_heuristic")

        height, width = face_crop.shape[:2]
        if min(width, height) < self.min_face_size:
            return self._reject(
                "face_too_small_for_liveness",
                score=0.0,
                method="rgb_heuristic",
                metrics={"width": int(width), "height": int(height)},
            )

        if self.model_path:
            try:
                score = self._predict_with_onnx(face_crop)
                return self._decision(score, method="onnx")
            except Exception as exc:
                heuristic = self._predict_with_heuristics(face_crop)
                metrics = dict(heuristic.metrics or {})
                metrics["modelError"] = str(exc)
                heuristic.metrics = metrics
                heuristic.method = "rgb_heuristic_fallback"
                return heuristic

        return self._predict_with_heuristics(face_crop)

    def status(self):
        """Return current detector configuration."""
        return {
            "enabled": self.enabled,
            "threshold": self.threshold,
            "minFaceSize": self.min_face_size,
            "modelPath": str(self.model_path) if self.model_path else None,
            "method": "onnx" if self.model_path else "rgb_heuristic",
        }

    def _predict_with_onnx(self, face_crop):
        import cv2
        import numpy as np
        import onnxruntime as ort

        if not self.model_path.exists():
            raise FileNotFoundError(f"Liveness model not found: {self.model_path}")

        if self._session is None:
            self._session = ort.InferenceSession(str(self.model_path), providers=["CPUExecutionProvider"])
            self._input_name = self._session.get_inputs()[0].name

        width, height = self.input_size
        resized = cv2.resize(face_crop, (width, height))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype("float32") / 255.0
        tensor = np.transpose(rgb, (2, 0, 1))[None, ...]
        outputs = self._session.run(None, {self._input_name: tensor})
        return _score_from_model_output(outputs[0])

    def _predict_with_heuristics(self, face_crop):
        import cv2
        import numpy as np

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(face_crop, cv2.COLOR_BGR2HSV)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        gray_std = float(gray.std())
        color_std = float(np.mean(np.std(face_crop, axis=(0, 1))))
        saturation_mean = float(hsv[:, :, 1].mean())
        edges = cv2.Canny(gray, 60, 160)
        edge_density = float((edges > 0).mean())

        sharpness_score = min(1.0, laplacian_var / 120.0)
        texture_score = min(1.0, gray_std / 45.0)
        color_score = min(1.0, color_std / 45.0)
        saturation_score = min(1.0, saturation_mean / 80.0)
        edge_score = min(1.0, edge_density / 0.08)
        score = (
            0.30 * sharpness_score
            + 0.25 * texture_score
            + 0.20 * color_score
            + 0.15 * saturation_score
            + 0.10 * edge_score
        )

        metrics = {
            "laplacianVar": round(laplacian_var, 4),
            "grayStd": round(gray_std, 4),
            "colorStd": round(color_std, 4),
            "saturationMean": round(saturation_mean, 4),
            "edgeDensity": round(edge_density, 4),
        }

        result = self._decision(score, method="rgb_heuristic", metrics=metrics)
        if not result.passed:
            result.reject_reason = "liveness_failed"
        return result

    def _decision(self, score, method, metrics=None):
        score = round(float(max(0.0, min(1.0, score))), 4)
        passed = score >= self.threshold
        return LivenessResult(
            enabled=True,
            passed=passed,
            score=score,
            threshold=self.threshold,
            method=method,
            reject_reason=None if passed else "liveness_failed",
            metrics=metrics,
        )

    def _reject(self, reason, score, method, metrics=None):
        return LivenessResult(
            enabled=True,
            passed=False,
            score=round(float(score), 4),
            threshold=self.threshold,
            method=method,
            reject_reason=reason,
            metrics=metrics,
        )


def _score_from_model_output(output):
    import numpy as np

    values = np.asarray(output, dtype="float32").reshape(-1)
    if values.size == 0:
        return 0.0
    if values.size == 1:
        return _sigmoid(float(values[0]))

    exp_values = np.exp(values - np.max(values))
    probs = exp_values / exp_values.sum()
    return float(probs[-1])


def _sigmoid(value):
    import math

    return 1.0 / (1.0 + math.exp(-value))
