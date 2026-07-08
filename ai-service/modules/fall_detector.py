import math


class FallDetector:
    """Detect possible fall events from recent person pose or bbox history."""

    def __init__(
        self,
        ratio_threshold: float = 1.2,
        confirm_frames: int = 5,
        min_confidence: float = 0.6,
        pose_horizontal_angle_threshold: float = 35.0,
        pose_min_keypoint_confidence: float = 0.3,
    ):
        """Initialize fall thresholds for pose-first detection and bbox fallback."""
        self.ratio_threshold = float(ratio_threshold)
        self.confirm_frames = int(confirm_frames)
        self.min_confidence = float(min_confidence)
        self.pose_horizontal_angle_threshold = float(pose_horizontal_angle_threshold)
        self.pose_min_keypoint_confidence = float(pose_min_keypoint_confidence)

    def detect(self, track_history):
        """Return FALL_ALERT-style result from one track history."""
        recent_history = self._get_recent_history(track_history)
        if not recent_history:
            return None

        frame_scores = [self._fall_score(entry) for entry in recent_history]
        fall_scores = [score for score in frame_scores if score["isFallLike"]]
        latest = recent_history[-1]
        duration_frames = len(fall_scores)
        is_fall = duration_frames >= self.confirm_frames
        confidence = self._calculate_confidence(fall_scores)
        evidence = self._summarize_evidence(frame_scores)

        return {
            "type": "FALL_ALERT",
            "trackId": latest.get("trackId"),
            "isFall": is_fall,
            "confidence": confidence,
            "durationFrames": duration_frames,
            "evidenceType": evidence["evidenceType"],
            "evidence": evidence,
            "level": self._get_level(is_fall, confidence),
        }

    def _get_recent_history(self, track_history):
        """Keep only the recent frames needed for fall confirmation."""
        if not track_history:
            return []
        return list(track_history)[-self.confirm_frames :]

    def _fall_score(self, entry):
        """Score one frame using pose keypoints first and bbox shape as fallback."""
        pose_score = self._pose_fall_score(entry)
        if pose_score is not None:
            return pose_score

        return self._bbox_fall_score(entry)

    def _pose_fall_score(self, entry):
        """Return pose-based fall score when shoulder and hip points are usable."""
        keypoints = self._normalize_keypoints(
            entry.get("keypoints") or entry.get("poseKeypoints") or entry.get("pose")
        )
        if not keypoints:
            return None

        shoulder = self._body_midpoint(keypoints, 5, 6, "left_shoulder", "right_shoulder")
        hip = self._body_midpoint(keypoints, 11, 12, "left_hip", "right_hip")
        if shoulder is None or hip is None:
            return None

        angle = self._angle_from_horizontal(shoulder, hip)
        is_fall_like = angle <= self.pose_horizontal_angle_threshold
        score = 1.0 if is_fall_like else max(0.0, 1.0 - (angle / 90.0))
        return {
            "isFallLike": is_fall_like,
            "score": round(score, 2),
            "evidenceType": "pose",
            "bodyAngle": round(angle, 2),
            "threshold": self.pose_horizontal_angle_threshold,
        }

    def _bbox_fall_score(self, entry):
        """Return bbox-based score for models that do not output pose keypoints yet."""
        bbox = entry.get("bbox")
        width, height = self._get_bbox_size(bbox)
        if height <= 0:
            return {
                "isFallLike": False,
                "score": 0.0,
                "evidenceType": "bbox",
                "ratio": 0.0,
                "threshold": self.ratio_threshold,
            }

        ratio = width / height
        is_fall_like = ratio >= self.ratio_threshold
        score = min(1.0, ratio / self.ratio_threshold) if self.ratio_threshold > 0 else 0.0
        return {
            "isFallLike": is_fall_like,
            "score": round(score, 2),
            "evidenceType": "bbox",
            "ratio": round(ratio, 2),
            "threshold": self.ratio_threshold,
        }

    def _get_bbox_size(self, bbox):
        """Extract bbox width and height from dict or tuple."""
        if isinstance(bbox, dict):
            width = bbox.get("x2", 0) - bbox.get("x1", 0)
            height = bbox.get("y2", 0) - bbox.get("y1", 0)
            return width, height

        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            return x2 - x1, y2 - y1

        return 0, 0

    def _calculate_confidence(self, fall_scores):
        """Calculate confidence from confirmed fall-like frame count."""
        if self.confirm_frames <= 0:
            return 0.0
        if not fall_scores:
            return 0.0

        duration_ratio = len(fall_scores) / self.confirm_frames
        evidence_score = sum(item.get("score", 0.0) for item in fall_scores) / len(fall_scores)
        confidence = min(1.0, duration_ratio) * evidence_score
        return round(min(1.0, max(0.0, confidence)), 2)

    def _summarize_evidence(self, frame_scores):
        """Summarize score evidence without storing image data."""
        if not frame_scores:
            return {"evidenceType": "none", "fallLikeFrames": 0, "totalFrames": 0}

        pose_frames = [score for score in frame_scores if score.get("evidenceType") == "pose"]
        bbox_frames = [score for score in frame_scores if score.get("evidenceType") == "bbox"]
        fall_like_frames = [score for score in frame_scores if score.get("isFallLike")]
        evidence_type = "pose" if pose_frames else "bbox"
        latest = frame_scores[-1]
        summary = {
            "evidenceType": evidence_type,
            "fallLikeFrames": len(fall_like_frames),
            "totalFrames": len(frame_scores),
            "poseFrames": len(pose_frames),
            "bboxFrames": len(bbox_frames),
            "latestScore": latest.get("score", 0.0),
        }
        for key in ("bodyAngle", "ratio", "threshold"):
            if key in latest:
                summary[f"latest{key[0].upper()}{key[1:]}"] = latest[key]
        return summary

    def _get_level(self, is_fall, confidence):
        """Map fall state and confidence to alert level."""
        if is_fall and confidence >= self.min_confidence:
            return "high"
        if confidence > 0:
            return "medium"
        return "low"

    def _normalize_keypoints(self, keypoints):
        """Normalize common keypoint formats into dictionaries with x, y, and confidence."""
        if not isinstance(keypoints, list):
            return []

        normalized = []
        for index, point in enumerate(keypoints):
            if isinstance(point, dict):
                normalized.append(
                    {
                        "index": _to_int(point.get("index", point.get("id", index)), index),
                        "name": point.get("name") or point.get("part"),
                        "x": _to_float(point.get("x")),
                        "y": _to_float(point.get("y")),
                        "confidence": _to_float(
                            point.get("confidence", point.get("score", point.get("visibility", 1.0)))
                        ),
                    }
                )
                continue

            if isinstance(point, (list, tuple)) and len(point) >= 2:
                normalized.append(
                    {
                        "index": index,
                        "name": None,
                        "x": _to_float(point[0]),
                        "y": _to_float(point[1]),
                        "confidence": _to_float(point[2]) if len(point) >= 3 else 1.0,
                    }
                )

        return normalized

    def _body_midpoint(self, keypoints, left_index, right_index, left_name, right_name):
        left = self._keypoint(keypoints, left_index, left_name)
        right = self._keypoint(keypoints, right_index, right_name)
        points = [point for point in (left, right) if self._is_usable_point(point)]
        if not points:
            return None

        return (
            sum(point["x"] for point in points) / len(points),
            sum(point["y"] for point in points) / len(points),
        )

    def _keypoint(self, keypoints, index, name):
        for point in keypoints:
            if point.get("index") == index or point.get("name") == name:
                return point
        return None

    def _is_usable_point(self, point):
        if not point:
            return False
        if point.get("x") is None or point.get("y") is None:
            return False
        confidence = point.get("confidence")
        if confidence is None:
            return False
        return confidence >= self.pose_min_keypoint_confidence

    def _angle_from_horizontal(self, point_a, point_b):
        dx = point_b[0] - point_a[0]
        dy = point_b[1] - point_a[1]
        if dx == 0 and dy == 0:
            return 90.0

        angle = abs(math.degrees(math.atan2(dy, dx)))
        if angle > 90.0:
            angle = 180.0 - angle
        return angle


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
