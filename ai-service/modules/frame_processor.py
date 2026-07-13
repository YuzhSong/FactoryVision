from datetime import datetime, timezone
from copy import deepcopy
import math
import time

from .abnormal_behavior_service import AbnormalBehaviorService
from .employee_presence_detector import EmployeePresenceDetector
from .employee_recognition_detector import EmployeeRecognitionDetector
from .event_classification import enrich_event_classification
from .stranger_detector import StrangerDetector
from .identity_cache import FaceIdentityCache


REPLAY_EVENT_TYPES = {
    "HELMET_WARNING",
    "ZONE_WARNING",
    "RUNNING_ALERT",
    "STRANGER_DETECTED",
    "STRANGER_ALERT",
    "FACE_RECOGNIZED",
    "FALL_ALERT",
    "FALL_DETECTED",
}


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
        self.abnormal_config = abnormal_config
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
        self.employee_recognition_detector = EmployeeRecognitionDetector(
            employee_cooldown_seconds=abnormal_config.get("faceRecognizedCooldownSeconds", 60.0),
            track_ttl_seconds=abnormal_config.get("faceTrackTtlSeconds", 30.0),
        )
        self.track_histories = {}
        self.history_limit = history_limit
        self.identity_cache = FaceIdentityCache(
            ttl_seconds=abnormal_config.get("faceIdentityCacheSeconds", 5.0),
            unknown_ttl_seconds=abnormal_config.get("faceUnknownCacheSeconds", 1.0),
            track_ttl_seconds=abnormal_config.get("faceTrackTtlSeconds", 30.0),
            clock=abnormal_config.get("clock"),
        )

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
        person_detections: list[dict] | None = None,
        helmet_detections: list[dict] | None = None,
        run_person_detection: bool = True,
        run_helmet_detection: bool = True,
        run_face_recognition: bool | None = None,
    ):
        """Process one frame into a unified AI report payload."""
        timestamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat()
        frame_id = frame_id or f"frame-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        if zones is not None:
            self.abnormal_service.zone_detector.set_zones(zones)

        timings = {}
        if run_person_detection:
            started_at = time.perf_counter()
            person_results = self.person_detector.detect(frame, frame_id=frame_id)
            timings["person"] = _elapsed_ms(started_at)
        else:
            person_results = deepcopy(person_detections or [])

        if run_helmet_detection:
            started_at = time.perf_counter()
            helmet_results = self.abnormal_service.helmet_detector.detect(
                frame,
                person_detections=person_results,
                frame_id=frame_id,
            )
            timings["helmet"] = _elapsed_ms(started_at)
        else:
            helmet_results = deepcopy(helmet_detections or [])
        self._apply_helmet_results(person_results, helmet_results)
        # Cached boxes are for drawing/rule continuity only. Treating them as fresh
        # observations made one detector result look like five temporal fall samples.
        if run_person_detection:
            self._update_track_histories(
                person_results,
                timestamp=timestamp,
                frame_index=frame_index,
                fps=fps,
                frame_shape=getattr(frame, "shape", None),
            )

        started_at = time.perf_counter()
        report = self.abnormal_service.build_ai_report(
            camera_id=camera_id,
            frame_id=frame_id,
            person_detections=person_results,
            track_histories=self.track_histories,
            timestamp=timestamp,
            frame_shape=getattr(frame, "shape", None),
        )
        behavior_ms = _elapsed_ms(started_at)
        behavior_timings = (
            getattr(self.abnormal_service, "last_diagnostics", {}).get("timingsMs", {})
            if getattr(self.abnormal_service, "last_diagnostics", None)
            else {}
        )
        timings["zoneRules"] = behavior_timings.get("zoneRules", behavior_ms)
        timings["fall"] = behavior_timings.get("fall", 0.0)
        report["diagnostics"] = {
            "helmet": dict(getattr(self.abnormal_service.helmet_detector, "last_diagnostics", {}) or {}),
            "behavior": dict(getattr(self.abnormal_service, "last_diagnostics", {}) or {}),
        }

        face_results = []
        run_face_recognition = include_faces if run_face_recognition is None else run_face_recognition
        visible_track_ids = [item.get("trackId") for item in person_results if item.get("trackId") not in (None, "")]
        self.identity_cache.purge_missing(camera_id, visible_track_ids)
        if include_faces and run_face_recognition and self.face_service is not None:
            started_at = time.perf_counter()
            face_results = self.face_service.recognize(
                frame,
                person_detections=person_results,
                frame_id=frame_id,
            )
            timings["face"] = _elapsed_ms(started_at)
            for face_result in face_results:
                self.identity_cache.put(camera_id, face_result)
        elif include_faces:
            face_results = self.identity_cache.results_for_tracks(camera_id, visible_track_ids)
        self.employee_recognition_detector.observe_tracks(camera_id, visible_track_ids, timestamp=timestamp)

        recognition_events = []
        if include_faces and run_face_recognition and self.face_service is not None:
            recognition_events = self.employee_recognition_detector.detect(
                face_results,
                camera_id=camera_id,
                frame_id=frame_id,
                timestamp=timestamp,
            )

        presence_results = []
        if include_faces and run_face_recognition and self.face_service is not None:
            presence_results = self.employee_presence_detector.detect(
                face_results,
                camera_id=camera_id,
                frame_id=frame_id,
                timestamp=timestamp,
            )

        stranger_results = []
        if include_faces and run_face_recognition and self.face_service is not None and self._face_library_ready():
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
        # Keep the separate PPE boxes so the processed stream can render them alongside people.
        report["results"] = enrich_event_classification(
            person_results
            + helmet_results
            + face_results
            + recognition_events
            + stranger_results
            + presence_results
            + non_person_results
        )
        self._attach_replay_evidence(report["results"])
        report["modelTimingsMs"] = timings
        report["modelRuns"] = {
            "person": bool(run_person_detection),
            "helmet": bool(run_helmet_detection),
            "face": bool(include_faces and run_face_recognition and self.face_service is not None),
            "fall": True,
        }
        return report

    def reset(self):
        """Reset track history and person detector tracking state."""
        self.track_histories = {}
        self.stranger_detector.reset()
        self.employee_presence_detector.reset()
        self.employee_recognition_detector.reset()
        self.abnormal_service.zone_detector.reset()
        self.identity_cache.clear()
        if hasattr(self.person_detector, "reset_tracks"):
            self.person_detector.reset_tracks()

    def _update_track_histories(
        self,
        person_results,
        timestamp: str,
        frame_index: int | None,
        fps: float | None,
        frame_shape=None,
    ):
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
            if frame_shape is not None:
                entry["frameShape"] = list(frame_shape[:2])
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

    def _attach_replay_evidence(self, results):
        """Attach bounded trajectory metadata to actionable results without storing frames."""
        for result in results or []:
            if not _is_replay_event(result):
                continue
            track_id = result.get("trackId")
            if track_id in (None, ""):
                continue
            history = self.track_histories.get(track_id) or self.track_histories.get(str(track_id)) or []
            trajectory = [_replay_point(entry) for entry in history[-self.history_limit:]]
            trajectory = [point for point in trajectory if point.get("center") or point.get("bbox")]
            if not trajectory:
                continue
            result.setdefault("trajectory", trajectory)
            result.setdefault("triggerPoint", trajectory[-1].get("center"))

    def _face_library_ready(self):
        if self.face_service is None or not hasattr(self.face_service, "status"):
            return False
        try:
            return int((self.face_service.status() or {}).get("loadedFaces") or 0) > 0
        except (TypeError, ValueError):
            return False


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


def _is_replay_event(result):
    event_type = result.get("type") or result.get("eventType")
    return event_type in REPLAY_EVENT_TYPES


def _replay_point(entry):
    point = {
        "timestamp": entry.get("timestamp"),
        "center": list(entry.get("center") or []),
        "bbox": list(entry.get("bbox") or []),
    }
    for key in ("speed", "frameIndex", "keypoints"):
        if key in entry:
            point[key] = entry[key]
    return {key: value for key, value in point.items() if value not in (None, [], {})}


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


def _elapsed_ms(started_at):
    return round((time.perf_counter() - started_at) * 1000, 2)
