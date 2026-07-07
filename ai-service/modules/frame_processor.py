from datetime import datetime, timezone

from .abnormal_behavior_service import AbnormalBehaviorService


class FrameProcessor:
    def __init__(
        self,
        person_detector,
        face_service=None,
        zones: list[dict] | None = None,
        history_limit: int = 30,
        abnormal_config: dict | None = None,
    ):
        self.person_detector = person_detector
        self.face_service = face_service
        self.abnormal_service = AbnormalBehaviorService(zones=zones or [], config=abnormal_config)
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
        timestamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat()
        frame_id = frame_id or f"frame-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        if zones is not None:
            self.abnormal_service.zone_detector.set_zones(zones)

        person_results = self.person_detector.detect(frame, frame_id=frame_id)
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

        non_person_results = [
            result
            for result in report["results"]
            if result.get("type") != "PERSON_DETECTION"
        ]
        report["results"] = person_results + face_results + non_person_results
        return report

    def reset(self):
        self.track_histories = {}
        if hasattr(self.person_detector, "reset_tracks"):
            self.person_detector.reset_tracks()

    def _update_track_histories(self, person_results, timestamp: str, frame_index: int | None, fps: float | None):
        for detection in person_results:
            track_id = detection.get("trackId")
            if not track_id:
                continue

            entry = dict(detection)
            entry["timestamp"] = timestamp
            if frame_index is not None:
                entry["frameIndex"] = frame_index
            if fps is not None:
                entry["fps"] = fps

            history = self.track_histories.setdefault(track_id, [])
            history.append(entry)
            if len(history) > self.history_limit:
                del history[:-self.history_limit]
