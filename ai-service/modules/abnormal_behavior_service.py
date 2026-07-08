from datetime import datetime, timezone

from .fall_detector import FallDetector
from .helmet_detector import HelmetDetector
from .running_detector import RunningDetector
from .zone_detector import ZoneDetector


class AbnormalBehaviorService:
    """Build behavior-related warnings from person detections and track histories."""

    def __init__(self, zones=None, config=None):
        """Initialize fall, running, helmet, and zone detectors."""
        config = config or {}
        self.fall_detector = FallDetector(
            ratio_threshold=config.get("fallRatioThreshold", 1.2),
            confirm_frames=config.get("fallConfirmFrames", 5),
            min_confidence=config.get("fallMinConfidence", 0.6),
            pose_horizontal_angle_threshold=config.get("fallPoseHorizontalAngleThreshold", 35.0),
            pose_min_keypoint_confidence=config.get("fallPoseMinKeypointConfidence", 0.3),
        )
        self.running_detector = RunningDetector(
            speed_threshold=config.get("runningSpeedThreshold", 30.0),
            confirm_frames=config.get("runningConfirmFrames", 5),
        )
        self.helmet_detector = HelmetDetector(
            confidence_threshold=config.get("helmetConfidenceThreshold", 0.6),
            model_path=config.get("helmetModelPath"),
            provider=config.get("helmetModelProvider", "opensource"),
            detection_confidence_threshold=config.get("helmetDetectionConfidenceThreshold", 0.35),
            iou_threshold=config.get("helmetIouThreshold", 0.45),
            device=config.get("helmetDevice", "auto"),
            image_size=config.get("helmetImageSize", 640),
            half_precision=config.get("helmetHalfPrecision", "auto"),
            cudnn_benchmark=config.get("helmetCudnnBenchmark", True),
            match_upper_ratio=config.get("helmetMatchUpperRatio", 0.65),
            class_ids=config.get("helmetClassIds", (1, 2)),
            helmet_class_id=config.get("helmetClassId", 1),
            no_helmet_class_id=config.get("noHelmetClassId", 2),
        )
        self.zone_detector = ZoneDetector(
            zones=zones,
            min_stay_seconds=config.get("zoneMinStaySeconds", 10.0),
            state_ttl_seconds=config.get("zoneStateTtlSeconds", 30.0),
        )

    def build_ai_report(self, camera_id, frame_id, person_detections, track_histories=None, timestamp=None):
        """Build one AI report with person detections and behavior warnings."""
        results = []
        person_detections = person_detections or []
        track_histories = track_histories or {}

        results.extend(person_detections)
        results.extend(self.zone_detector.detect_intrusion(person_detections, timestamp=timestamp))

        for detection in person_detections:
            track_id = detection.get("trackId")
            if not track_id:
                continue

            history = track_histories.get(track_id, [])
            fall_result = self.fall_detector.detect(history)
            if fall_result and fall_result.get("isFall"):
                results.append(fall_result)

            running_result = self.running_detector.detect(history)
            if running_result and running_result.get("isRunning"):
                results.append(running_result)

            helmet_result = self._build_helmet_result(detection)
            if helmet_result:
                results.append(helmet_result)

        return {
            "cameraId": camera_id,
            "frameId": frame_id,
            "timestamp": timestamp or self._now_iso(),
            "results": results,
        }

    def _build_helmet_result(self, detection):
        """Format helmet warning when detection contains helmet status fields."""
        helmet_status = detection.get("helmetStatus") or detection.get("helmet_status")
        helmet_confidence = detection.get("helmetConfidence") or detection.get("helmet_confidence")
        if helmet_status is None or helmet_confidence is None:
            return None
        return self.helmet_detector.format_warning(
            track_id=detection.get("trackId"),
            helmet_status=helmet_status,
            confidence=helmet_confidence,
        )

    def _now_iso(self):
        """Return current local ISO timestamp."""
        return datetime.now(timezone.utc).astimezone().isoformat()
