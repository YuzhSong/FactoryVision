from datetime import datetime, timezone
import logging
import time

from .fall_detector import FallDetector
from .helmet_detector import HelmetDetector
from .running_detector import RunningDetector
from .zone_detector import ZoneDetector


logger = logging.getLogger("uvicorn.error")


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
            bbox_edge_margin_ratio=config.get("fallBboxEdgeMarginRatio", 0.02),
            min_center_drop_ratio=config.get("fallMinCenterDropRatio", 0.15),
            min_height_drop_ratio=config.get("fallMinHeightDropRatio", 0.2),
            max_transition_seconds=config.get("fallMaxTransitionSeconds", 2.0),
            sustained_low_drop_ratio=config.get("fallSustainedLowDropRatio", 0.4),
            low_posture_height_ratio=config.get("fallLowPostureHeightRatio", 0.7),
            very_low_height_ratio=config.get("fallVeryLowHeightRatio", 0.58),
            slow_transition_seconds=config.get("fallSlowTransitionSeconds", 6.0),
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
            max_det=config.get("helmetMaxDet", 300),
            class_ids=config.get("helmetClassIds", (1, 2)),
            helmet_class_id=config.get("helmetClassId", 1),
            no_helmet_class_id=config.get("noHelmetClassId", 2),
        )
        self.zone_detector = ZoneDetector(
            zones=zones,
            min_stay_seconds=config.get("zoneMinStaySeconds", 10.0),
            state_ttl_seconds=config.get("zoneStateTtlSeconds", 30.0),
            enter_confirm_seconds=config.get("zoneEnterConfirmSeconds", 0.3),
            exit_confirm_seconds=config.get("zoneExitConfirmSeconds", 1.0),
        )
        self.helmet_event_cooldown_seconds = max(0.0, float(config.get("helmetEventCooldownSeconds", 20.0)))
        self.track_state_ttl_seconds = max(1.0, float(config.get("trackStateTtlSeconds", 30.0)))
        self.fall_recover_frames = max(1, int(config.get("fallRecoverFrames", 2)))
        self.fall_state_ttl_seconds = max(1.0, float(config.get("fallStateTtlSeconds", self.track_state_ttl_seconds)))
        self._helmet_states = {}
        self._fall_states = {}
        self.last_diagnostics = {}
        self._last_behavior_log_at = 0.0
        self.clock = config.get("clock") or time.monotonic

    def build_ai_report(
        self,
        camera_id,
        frame_id,
        person_detections,
        track_histories=None,
        timestamp=None,
        frame_shape=None,
    ):
        """Build one AI report with person detections and behavior warnings."""
        results = []
        person_detections = person_detections or []
        track_histories = track_histories or {}
        now = self.clock()
        visible_keys = {(str(camera_id), str(item.get("trackId")), "HELMET_WARNING") for item in person_detections if item.get("trackId") not in (None, "")}
        self._purge_helmet_states(now, visible_keys)
        visible_fall_keys = {(str(camera_id), str(item.get("trackId"))) for item in person_detections if item.get("trackId") not in (None, "")}
        self._purge_fall_states(now, visible_fall_keys)
        for key in visible_keys:
            if key in self._helmet_states:
                self._helmet_states[key]["lastSeenAt"] = now

        results.extend(person_detections)
        zone_started_at = time.perf_counter()
        zone_results = self.zone_detector.detect_events(
            camera_id=camera_id,
            detections=person_detections,
            timestamp=timestamp,
            frame_shape=frame_shape,
        )
        zone_ms = _elapsed_ms(zone_started_at)
        results.extend(zone_results)

        fall_ms = 0.0
        fall_observations = []
        for detection in person_detections:
            track_id = detection.get("trackId")
            if not track_id:
                continue

            history = track_histories.get(track_id, [])
            fall_started_at = time.perf_counter()
            fall_result = self.fall_detector.detect(history)
            if fall_result:
                fall_observations.append(
                    {
                        "trackId": str(track_id),
                        "state": self._fall_states.get((str(camera_id), str(track_id)), {}).get("state", "normal"),
                        "isFall": bool(fall_result.get("isFall")),
                        "ruleScore": fall_result.get("confidence"),
                        "confidenceType": fall_result.get("confidenceType"),
                        "rejectionReason": (fall_result.get("evidence") or {}).get("rejectionReason"),
                        "evidence": fall_result.get("evidence"),
                    }
                )
            fall_event = self._build_fall_result(camera_id, detection, fall_result)
            fall_ms += _elapsed_ms(fall_started_at)
            if fall_event:
                results.append(fall_event)

            running_result = self.running_detector.detect(history)
            if running_result and running_result.get("isRunning"):
                results.append(running_result)

            helmet_result = self._build_helmet_result(camera_id, detection)
            if helmet_result:
                results.append(helmet_result)

        self.last_diagnostics = {
            "zoneEventCount": len(zone_results),
            "zone": dict(getattr(self.zone_detector, "last_diagnostics", {}) or {}),
            "fallStateCount": len(self._fall_states),
            "fallObservations": fall_observations[:10],
            "timingsMs": {
                "zoneRules": round(zone_ms, 2),
                "fall": round(fall_ms, 2),
            },
        }
        if now - self._last_behavior_log_at >= 10.0:
            self._last_behavior_log_at = now
            logger.info(
                "behavior diagnostics camera=%s zones=%s zone_events=%s fall_states=%s",
                camera_id,
                self.last_diagnostics.get("zone"),
                len(zone_results),
                len(self._fall_states),
            )

        return {
            "cameraId": camera_id,
            "frameId": frame_id,
            "timestamp": timestamp or self._now_iso(),
            "results": results,
        }

    def _build_fall_result(self, camera_id, detection, fall_result):
        """Emit one fall event per continuous fallen state and reset after recovery."""
        track_id = detection.get("trackId")
        if not track_id or not fall_result:
            return None

        now = self.clock()
        key = (str(camera_id), str(track_id))
        state = self._fall_states.setdefault(
            key,
            {
                "state": "normal",
                "reported": False,
                "normalFrames": 0,
                "lastSeenAt": now,
            },
        )
        state["lastSeenAt"] = now

        observation_id = fall_result.get("observationId")
        if observation_id is not None and state.get("lastObservationId") == observation_id:
            return None
        state["lastObservationId"] = observation_id

        is_confirmed_fall = bool(fall_result.get("isFall")) and float(fall_result.get("confidence") or 0) >= self.fall_detector.min_confidence
        if is_confirmed_fall:
            state["normalFrames"] = 0
            if state["state"] != "fallen":
                state["state"] = "fallen"
                state["reported"] = False
            if state["reported"]:
                return None
            state["reported"] = True
            event = dict(fall_result)
            event["cameraId"] = camera_id
            event["trackId"] = str(track_id)
            event["eventType"] = "fall_detected"
            event["fallState"] = "fallen"
            event["bbox"] = detection.get("bbox")
            return event

        if state["state"] == "fallen":
            state["state"] = "recovered"
            state["normalFrames"] = 1
            return None
        if state["state"] == "recovered":
            state["normalFrames"] += 1
            if state["normalFrames"] >= self.fall_recover_frames:
                state["state"] = "normal"
                state["reported"] = False
        return None

    def _build_helmet_result(self, camera_id, detection):
        """Format helmet warning when detection contains helmet status fields."""
        now = self.clock()
        helmet_status = detection.get("helmetStatus") or detection.get("helmet_status")
        helmet_confidence = detection.get("helmetConfidence") or detection.get("helmet_confidence")
        if helmet_status is None or helmet_confidence is None:
            return None
        track_id = detection.get("trackId")
        if track_id in (None, "") or helmet_status == "unknown":
            return None
        key = (str(camera_id), str(track_id), "HELMET_WARNING")
        state = self._helmet_states.get(key)
        if helmet_status == "helmet":
            self._helmet_states.pop(key, None)
            return None
        warning = self.helmet_detector.format_warning(
            track_id=detection.get("trackId"),
            helmet_status=helmet_status,
            confidence=helmet_confidence,
        )
        if warning is None:
            return None
        if state and now - state["lastReportedAt"] < self.helmet_event_cooldown_seconds:
            state["lastSeenAt"] = now
            return None
        self._helmet_states[key] = {"lastReportedAt": now, "lastSeenAt": now}
        warning["cameraId"] = camera_id
        return warning

    def _purge_helmet_states(self, now, visible_keys=None):
        visible_keys = visible_keys or set()
        self._helmet_states = {
            key: state for key, state in self._helmet_states.items()
            if key in visible_keys or now - state["lastSeenAt"] <= self.track_state_ttl_seconds
        }

    def _purge_fall_states(self, now, visible_keys=None):
        visible_keys = visible_keys or set()
        self._fall_states = {
            key: state for key, state in self._fall_states.items()
            if key in visible_keys or now - state["lastSeenAt"] <= self.fall_state_ttl_seconds
        }

    def _now_iso(self):
        """Return current local ISO timestamp."""
        return datetime.now(timezone.utc).astimezone().isoformat()


def _elapsed_ms(started_at):
    return (time.perf_counter() - started_at) * 1000
