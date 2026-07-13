from datetime import datetime
import math


class FallDetector:
    """Detect a sustained fall transition from real per-track observations."""

    def __init__(
        self,
        ratio_threshold: float = 1.2,
        confirm_frames: int = 5,
        min_confidence: float = 0.6,
        pose_horizontal_angle_threshold: float = 35.0,
        pose_min_keypoint_confidence: float = 0.3,
        bbox_edge_margin_ratio: float = 0.02,
        min_center_drop_ratio: float = 0.15,
        min_height_drop_ratio: float = 0.2,
        max_transition_seconds: float = 2.0,
    ):
        self.ratio_threshold = float(ratio_threshold)
        self.confirm_frames = max(2, int(confirm_frames))
        self.min_confidence = float(min_confidence)
        self.pose_horizontal_angle_threshold = float(pose_horizontal_angle_threshold)
        self.pose_min_keypoint_confidence = float(pose_min_keypoint_confidence)
        self.bbox_edge_margin_ratio = max(0.0, float(bbox_edge_margin_ratio))
        self.min_center_drop_ratio = max(0.0, float(min_center_drop_ratio))
        self.min_height_drop_ratio = max(0.0, float(min_height_drop_ratio))
        self.max_transition_seconds = max(0.01, float(max_transition_seconds))

    def detect(self, track_history):
        """Return a rule score; only a sustained transition can become a fall event."""
        history = list(track_history or [])
        latest = history[-1] if history else {}
        observation_id = latest.get("frameIndex", latest.get("timestamp"))
        if len(history) < self.confirm_frames:
            return self._result(latest, False, 0.0, [], None, observation_id, "insufficient_history")

        recent = history[-self.confirm_frames :]
        frame_scores = [self._fall_score(entry) for entry in recent]
        fall_like = [score for score in frame_scores if score["isFallLike"]]
        all_consecutive = len(fall_like) == self.confirm_frames
        baseline = self._find_upright_baseline(history[: -self.confirm_frames])
        transition = self._transition_evidence(baseline, recent[0]) if baseline else None

        rejection_reason = None
        if any(score.get("rejectionReason") for score in frame_scores):
            rejection_reason = next(score["rejectionReason"] for score in frame_scores if score.get("rejectionReason"))
        elif not all_consecutive:
            rejection_reason = "not_consecutive"
        elif baseline is None:
            rejection_reason = "no_upright_baseline"
        elif not transition["fastEnough"]:
            rejection_reason = "transition_too_slow"
        elif not transition["hasDrop"]:
            rejection_reason = "no_downward_transition"

        is_fall = rejection_reason is None
        confidence = self._calculate_rule_score(frame_scores, transition) if is_fall else 0.0
        if is_fall and confidence < self.min_confidence:
            is_fall = False
            rejection_reason = "rule_score_below_threshold"

        return self._result(
            latest,
            is_fall,
            confidence,
            frame_scores,
            transition,
            observation_id,
            rejection_reason,
        )

    def _result(self, latest, is_fall, confidence, frame_scores, transition, observation_id, rejection_reason):
        evidence = self._summarize_evidence(frame_scores, transition, rejection_reason)
        return {
            "type": "FALL_ALERT",
            "trackId": latest.get("trackId"),
            "isFall": bool(is_fall),
            "confidence": round(float(confidence), 4),
            "confidenceType": "rule_composite_score",
            "durationFrames": sum(1 for score in frame_scores if score.get("isFallLike")),
            "evidenceType": evidence["evidenceType"],
            "evidence": evidence,
            "observationId": observation_id,
            "level": self._get_level(is_fall, confidence),
        }

    def _fall_score(self, entry):
        pose_score = self._pose_fall_score(entry)
        if pose_score is not None:
            return pose_score
        return self._bbox_fall_score(entry)

    def _pose_fall_score(self, entry):
        keypoints = self._normalize_keypoints(entry.get("keypoints") or entry.get("poseKeypoints") or entry.get("pose"))
        if not keypoints:
            return None
        shoulder = self._body_midpoint(keypoints, 5, 6, "left_shoulder", "right_shoulder")
        hip = self._body_midpoint(keypoints, 11, 12, "left_hip", "right_hip")
        if shoulder is None or hip is None:
            return None
        angle = self._angle_from_horizontal(shoulder, hip)
        score = _clamp(1.0 - (angle / 90.0))
        return {
            "isFallLike": angle <= self.pose_horizontal_angle_threshold,
            "score": round(score, 4),
            "evidenceType": "pose",
            "bodyAngle": round(angle, 2),
            "threshold": self.pose_horizontal_angle_threshold,
        }

    def _bbox_fall_score(self, entry):
        bbox = self._bbox(entry.get("bbox"))
        if bbox is None:
            return self._empty_bbox_score("invalid_bbox")
        x1, y1, x2, y2 = bbox
        width, height = x2 - x1, y2 - y1
        if height <= 0 or width <= 0:
            return self._empty_bbox_score("invalid_bbox")
        if self._is_edge_truncated(bbox, entry.get("frameShape")):
            score = self._empty_bbox_score("edge_truncated")
            score["ratio"] = round(width / height, 2)
            return score
        ratio = width / height
        # At the decision boundary the shape component is 0.5, not 1.0. It only
        # approaches one for a much more horizontal body.
        excess = max(0.0, ratio - self.ratio_threshold)
        score = 0.5 + (0.5 * _clamp(excess / max(self.ratio_threshold, 1e-6))) if ratio >= self.ratio_threshold else 0.5 * _clamp(ratio / max(self.ratio_threshold, 1e-6))
        return {
            "isFallLike": ratio >= self.ratio_threshold,
            "score": round(score, 4),
            "evidenceType": "bbox",
            "ratio": round(ratio, 2),
            "threshold": self.ratio_threshold,
        }

    def _empty_bbox_score(self, reason):
        return {
            "isFallLike": False,
            "score": 0.0,
            "evidenceType": "bbox",
            "ratio": 0.0,
            "threshold": self.ratio_threshold,
            "rejectionReason": reason,
        }

    def _find_upright_baseline(self, earlier_history):
        for entry in reversed(earlier_history):
            score = self._fall_score(entry)
            if not score.get("isFallLike") and not score.get("rejectionReason"):
                return entry
        return None

    def _transition_evidence(self, baseline, first_fall_like):
        base_bbox = self._bbox(baseline.get("bbox"))
        fall_bbox = self._bbox(first_fall_like.get("bbox"))
        if base_bbox is None or fall_bbox is None:
            return {"hasDrop": False, "fastEnough": False, "centerDropRatio": 0.0, "heightDropRatio": 0.0, "elapsedSeconds": None}
        base_height = max(1e-6, base_bbox[3] - base_bbox[1])
        fall_height = max(1e-6, fall_bbox[3] - fall_bbox[1])
        base_center_y = (base_bbox[1] + base_bbox[3]) / 2
        fall_center_y = (fall_bbox[1] + fall_bbox[3]) / 2
        center_drop_ratio = (fall_center_y - base_center_y) / base_height
        height_drop_ratio = 1.0 - (fall_height / base_height)
        elapsed = _elapsed_seconds(baseline.get("timestamp"), first_fall_like.get("timestamp"))
        return {
            "centerDropRatio": round(center_drop_ratio, 4),
            "heightDropRatio": round(height_drop_ratio, 4),
            "elapsedSeconds": round(elapsed, 4) if elapsed is not None else None,
            "hasDrop": center_drop_ratio >= self.min_center_drop_ratio or height_drop_ratio >= self.min_height_drop_ratio,
            "fastEnough": elapsed is not None and 0 < elapsed <= self.max_transition_seconds,
        }

    def _calculate_rule_score(self, frame_scores, transition):
        shape_score = sum(score.get("score", 0.0) for score in frame_scores) / max(1, len(frame_scores))
        center_score = _clamp(transition.get("centerDropRatio", 0.0) / max(self.min_center_drop_ratio, 1e-6))
        height_score = _clamp(transition.get("heightDropRatio", 0.0) / max(self.min_height_drop_ratio, 1e-6))
        persistence_score = _clamp(len(frame_scores) / max(1, self.confirm_frames))
        return _clamp((0.45 * shape_score) + (0.25 * center_score) + (0.20 * height_score) + (0.10 * persistence_score))

    def _summarize_evidence(self, frame_scores, transition, rejection_reason):
        latest = frame_scores[-1] if frame_scores else {}
        summary = {
            "evidenceType": latest.get("evidenceType", "none"),
            "fallLikeFrames": sum(1 for score in frame_scores if score.get("isFallLike")),
            "totalFrames": len(frame_scores),
            "poseFrames": sum(1 for score in frame_scores if score.get("evidenceType") == "pose"),
            "bboxFrames": sum(1 for score in frame_scores if score.get("evidenceType") == "bbox"),
            "latestScore": latest.get("score", 0.0),
            "rejectionReason": rejection_reason,
        }
        for key in ("bodyAngle", "ratio", "threshold"):
            if key in latest:
                summary[f"latest{key[0].upper()}{key[1:]}"] = latest[key]
        if transition:
            summary["transition"] = transition
        return summary

    def _is_edge_truncated(self, bbox, frame_shape):
        if not isinstance(frame_shape, (list, tuple)) or len(frame_shape) < 2:
            return False
        height, width = float(frame_shape[0]), float(frame_shape[1])
        if height <= 0 or width <= 0:
            return False
        x1, y1, x2, y2 = bbox
        margin_x = width * self.bbox_edge_margin_ratio
        margin_y = height * self.bbox_edge_margin_ratio
        return x1 <= margin_x or y1 <= margin_y or x2 >= width - margin_x or y2 >= height - margin_y

    def _bbox(self, bbox):
        if isinstance(bbox, dict):
            return tuple(float(bbox.get(key, 0)) for key in ("x1", "y1", "x2", "y2"))
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return tuple(float(value) for value in bbox)
        return None

    def _get_level(self, is_fall, confidence):
        if is_fall and confidence >= self.min_confidence:
            return "high"
        if confidence > 0:
            return "medium"
        return "low"

    def _normalize_keypoints(self, keypoints):
        if not isinstance(keypoints, list):
            return []
        normalized = []
        for index, point in enumerate(keypoints):
            if isinstance(point, dict):
                normalized.append({"index": _to_int(point.get("index", point.get("id", index)), index), "name": point.get("name") or point.get("part"), "x": _to_float(point.get("x")), "y": _to_float(point.get("y")), "confidence": _to_float(point.get("confidence", point.get("score", point.get("visibility", 1.0))))})
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                normalized.append({"index": index, "name": None, "x": _to_float(point[0]), "y": _to_float(point[1]), "confidence": _to_float(point[2]) if len(point) >= 3 else 1.0})
        return normalized

    def _body_midpoint(self, keypoints, left_index, right_index, left_name, right_name):
        left = self._keypoint(keypoints, left_index, left_name)
        right = self._keypoint(keypoints, right_index, right_name)
        points = [point for point in (left, right) if self._is_usable_point(point)]
        if not points:
            return None
        return (sum(point["x"] for point in points) / len(points), sum(point["y"] for point in points) / len(points))

    def _keypoint(self, keypoints, index, name):
        return next((point for point in keypoints if point.get("index") == index or point.get("name") == name), None)

    def _is_usable_point(self, point):
        return bool(point and point.get("x") is not None and point.get("y") is not None and point.get("confidence") is not None and point.get("confidence") >= self.pose_min_keypoint_confidence)

    def _angle_from_horizontal(self, point_a, point_b):
        dx, dy = point_b[0] - point_a[0], point_b[1] - point_a[1]
        if dx == 0 and dy == 0:
            return 90.0
        angle = abs(math.degrees(math.atan2(dy, dx)))
        return 180.0 - angle if angle > 90.0 else angle


def _elapsed_seconds(previous, current):
    try:
        left = datetime.fromisoformat(str(previous).replace("Z", "+00:00")).timestamp()
        right = datetime.fromisoformat(str(current).replace("Z", "+00:00")).timestamp()
        return right - left
    except (TypeError, ValueError):
        return None


def _clamp(value):
    return min(1.0, max(0.0, float(value)))


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
