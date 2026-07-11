from datetime import datetime, timezone
import math

from .abnormal_behavior_service import AbnormalBehaviorService
from .employee_presence_detector import EmployeePresenceDetector
from .stranger_detector import StrangerDetector


class FrameProcessor:
    """Coordinate person detection, face recognition, and behavior report building."""

    def __init__(
        self,
        person_detector,
        face_service=None,
        zones: list[dict] | None = None,
        history_limit: int = 5,
        abnormal_config: dict | None = None,
    ):
        """Initialize frame processor with detectors, zones, and history settings."""
        self.person_detector = person_detector
        self.face_service = face_service
        abnormal_config = abnormal_config or {}
        self.abnormal_service = AbnormalBehaviorService(zones=zones or [], config=abnormal_config)
        self.stranger_detector = StrangerDetector(
            confirm_frames=abnormal_config.get("strangerConfirmFrames", 3),
            cooldown_seconds=abnormal_config.get("strangerCooldownSeconds", 30.0),
            match_distance_threshold=abnormal_config.get("strangerMatchDistanceThreshold", 80.0),
            state_ttl_seconds=abnormal_config.get("strangerStateTtlSeconds", 10.0),
        )
        self.employee_presence_detector = EmployeePresenceDetector(
            absence_timeout_seconds=abnormal_config.get("employeeAbsenceTimeoutSeconds", 60.0),
            min_similarity=abnormal_config.get("employeePresenceMinSimilarity", 0.0),
        )
        self.track_histories = {}
        self.history_limit = history_limit

    def process_frame(
        self,
        frame,
        camera_id=None,
        frame_id: str | None = None,
        timestamp: str | None = None,
        include_faces: bool = True,
        frame_index: int | None = None,
        fps: float | None = None,
        zones: list[dict] | None = None,
    ):
        """Process one frame into a unified AI report payload."""
        timestamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat()
        frame_id = frame_id or f"frame-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        if zones is not None:
            self.abnormal_service.zone_detector.set_zones(zones)

        person_results = self.person_detector.detect(frame, frame_id=frame_id)
        helmet_results = self.abnormal_service.helmet_detector.detect(
            frame,
            person_detections=person_results,
            frame_id=frame_id,
        )
        self._apply_helmet_results(person_results, helmet_results)
        self._update_track_histories(person_results, timestamp=timestamp, frame_index=frame_index, fps=fps)

        report = self.abnormal_service.build_ai_report(
            camera_id=camera_id,
            frame_id=frame_id,
            person_detections=person_results,
            track_histories=self.track_histories,
            timestamp=timestamp,
        )

        face_results = []
        if include_faces and self.face_service is not None:
            face_results = self.face_service.recognize(
                frame,
                person_detections=person_results,
                frame_id=frame_id,
            )

        presence_results = []
        if include_faces and self.face_service is not None:
            presence_results = self.employee_presence_detector.detect(
                face_results,
                camera_id=camera_id,
                frame_id=frame_id,
                timestamp=timestamp,
            )

        stranger_results = self.stranger_detector.detect(
            face_results,
            camera_id=camera_id,
            frame_id=frame_id,
            timestamp=timestamp,
        )

        non_person_results = [
            result
            for result in report["results"]
            if result.get("type") != "PERSON_DETECTION"
        ]
        report["results"] = person_results + face_results + stranger_results + presence_results + non_person_results
        return report

    def reset(self):
        """Reset track history and person detector tracking state."""
        self.track_histories = {}
        self.stranger_detector.reset()
        self.employee_presence_detector.reset()
        if hasattr(self.person_detector, "reset_tracks"):
            self.person_detector.reset_tracks()

    def _update_track_histories(self, person_results, timestamp: str, frame_index: int | None, fps: float | None):
        """Append lightweight per-track history for behavior rules."""
        for detection in person_results:
            track_id = detection.get("trackId")
            if not track_id:
                continue

            bbox = _bbox_to_list(detection.get("bbox"))
            center = _center_to_list(detection.get("centerPoint"), bbox)
            speed = self.calculate_speed(track_id, center, timestamp)
            entry = {
                "trackId": track_id,
                "timestamp": timestamp,
                "center": center,
                "bbox": bbox,
            }
            keypoints = _extract_keypoints(detection)
            if keypoints:
                entry["keypoints"] = keypoints
            if frame_index is not None:
                entry["frameIndex"] = frame_index
            if fps is not None:
                entry["fps"] = fps
            if speed is not None:
                entry["speed"] = round(speed, 2)

            history = self.track_histories.setdefault(track_id, [])
            history.append(entry)
            if len(history) > self.history_limit:
                del history[:-self.history_limit]

    def calculate_speed(self, track_id, current_center, current_timestamp):
        """
        Calculate pixel speed from lightweight track history.

        The calculation uses the latest stored center point for the same track_id,
        so it does not require continuous frames or any saved image data.
        """
        if not current_center or len(current_center) != 2:
            return None

        history = self.track_histories.get(track_id, [])
        if not history:
            return None

        previous = history[-1]
        previous_center = previous.get("center")
        if not previous_center or len(previous_center) != 2:
            return None

        elapsed_seconds = _elapsed_seconds(previous.get("timestamp"), current_timestamp)
        if elapsed_seconds <= 0:
            return None

        return math.dist(previous_center, current_center) / elapsed_seconds

    def _apply_helmet_results(self, person_results, helmet_results):
        """Attach best helmet status per track to person detections."""
        helmet_by_track = _best_helmet_by_track(helmet_results)
        for detection in person_results:
            helmet = helmet_by_track.get(detection.get("trackId"))
            if not helmet:
                continue
            detection["helmetStatus"] = helmet.get("helmetStatus")
            detection["helmetConfidence"] = helmet.get("helmetConfidence")
            detection["helmetClassName"] = helmet.get("className")


def _bbox_to_list(bbox):
    if isinstance(bbox, dict):
        return [
            float(bbox.get("x1", 0)),
            float(bbox.get("y1", 0)),
            float(bbox.get("x2", 0)),
            float(bbox.get("y2", 0)),
        ]
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        return [float(value) for value in bbox]
    return [0.0, 0.0, 0.0, 0.0]


def _center_to_list(center, bbox):
    if isinstance(center, dict):
        return [float(center.get("x", 0)), float(center.get("y", 0))]
    if isinstance(center, (list, tuple)) and len(center) == 2:
        return [float(center[0]), float(center[1])]

    x1, y1, x2, y2 = bbox
    return [(x1 + x2) / 2, (y1 + y2) / 2]


def _extract_keypoints(detection):
    """Keep pose keypoints in history when an upstream detector provides them."""
    keypoints = detection.get("keypoints") or detection.get("poseKeypoints") or detection.get("pose")
    if isinstance(keypoints, list):
        return keypoints
    return None


def _elapsed_seconds(previous_timestamp, current_timestamp):
    previous = _parse_timestamp(previous_timestamp)
    current = _parse_timestamp(current_timestamp)
    if previous is None or current is None:
        return 0.0
    return current - previous


def _parse_timestamp(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None


def _best_helmet_by_track(helmet_results):
    """Pick the strongest helmet result for each person track."""
    best_by_track = {}
    for result in helmet_results or []:
        track_id = result.get("trackId")
        if not track_id:
            continue

        current = best_by_track.get(track_id)
        if current is None or _helmet_priority(result) > _helmet_priority(current):
            best_by_track[track_id] = result
    return best_by_track


def _helmet_priority(result):
    """Prioritize no-helmet detections, then confidence."""
    severity = 1 if result.get("helmetStatus") == "no_helmet" else 0
    confidence = float(result.get("helmetConfidence") or 0)
    return severity, confidence
