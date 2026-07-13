from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import queue
import re
import threading


logger = logging.getLogger(__name__)


@dataclass
class FrameSample:
    """One lightweight frame sample for event media buffering."""

    frame: object
    frame_id: str | None
    timestamp: str | None


class EventMediaRecorder:
    """Save alert keyframes and short pre/post event clips from processed frames."""

    def __init__(
        self,
        output_dir: str | Path,
        enabled: bool = True,
        fps: float = 10.0,
        pre_event_seconds: float = 3.0,
        post_event_seconds: float = 3.0,
        cooldown_seconds: float = 10.0,
        image_extension: str = "jpg",
        finalize_queue_size: int = 2,
        media_ready_callback=None,
    ):
        self.output_dir = Path(output_dir)
        self.enabled = bool(enabled)
        self.fps = max(1.0, float(fps or 10.0))
        self.pre_event_frames = max(0, int(round(float(pre_event_seconds or 0) * self.fps)))
        self.post_event_frames = max(0, int(round(float(post_event_seconds or 0) * self.fps)))
        self.cooldown_seconds = max(0.0, float(cooldown_seconds or 0))
        self.image_extension = image_extension.lstrip(".") or "jpg"
        self.frame_buffer = deque(maxlen=self.pre_event_frames)
        self.active_clips = []
        self.last_event_seconds_by_key = {}
        self.media_ready_callback = media_ready_callback
        self._finalize_queue = queue.Queue(maxsize=max(1, int(finalize_queue_size or 1)))
        self._finalize_thread = None
        self._finalize_lock = threading.Lock()

    def record_frame(self, frame, frame_id=None, timestamp=None, report=None):
        """Record one processed frame and return event media metadata created on this frame."""
        if not self.enabled:
            return []

        current = FrameSample(_copy_frame(frame), frame_id, timestamp)
        completed = self._append_to_active_clips(current)
        created = self._create_media_for_report_events(current, report or {})
        self.frame_buffer.append(current)
        self._finalize_completed_clips(completed)
        return created

    def reset(self):
        """Clear buffered frames and cooldown state."""
        self.frame_buffer.clear()
        self.active_clips = []
        self.last_event_seconds_by_key = {}

    def flush(self):
        """Finalize any active clips with the frames collected so far."""
        clips = self.active_clips
        self.active_clips = []
        self._finalize_completed_clips(clips)
        self._finalize_queue.join()

    def set_media_ready_callback(self, callback):
        self.media_ready_callback = callback

    def _create_media_for_report_events(self, current, report):
        event_results = [result for result in report.get("results", []) if _is_event_result(result)]
        if not event_results:
            return []

        created = []
        event_seconds = _parse_timestamp(current.timestamp)
        for index, result in enumerate(event_results):
            event_key = _event_key(result)
            if self._is_in_cooldown(event_key, event_seconds):
                continue

            self.last_event_seconds_by_key[event_key] = event_seconds
            media = self._start_media_bundle(current, result, report, index)
            created.append(media)

        return created

    def _start_media_bundle(self, current, result, report, index):
        event_id = _event_id(current, result, index)
        event_dir = self.output_dir / _safe_path_part(str(report.get("cameraId", "unknown"))) / event_id
        event_dir.mkdir(parents=True, exist_ok=True)

        keyframe_path = event_dir / f"keyframe.{self.image_extension}"
        clip_path = event_dir / "clip.mp4"
        manifest_path = event_dir / "manifest.json"

        _write_image(keyframe_path, current.frame)
        frames = [FrameSample(_copy_frame(sample.frame), sample.frame_id, sample.timestamp) for sample in self.frame_buffer]
        frames.append(FrameSample(_copy_frame(current.frame), current.frame_id, current.timestamp))

        media = {
            "eventId": event_id,
            "eventType": result.get("type"),
            "eventSubType": result.get("eventType"),
            "cameraId": report.get("cameraId"),
            "frameId": current.frame_id,
            "timestamp": current.timestamp,
            "keyframePath": str(keyframe_path),
            "clipPath": str(clip_path),
            "manifestPath": str(manifest_path),
            "status": "recording",
            "preEventFrames": len(frames) - 1,
            "postEventFrames": self.post_event_frames,
        }
        if result is not None:
            result["mediaEventId"] = event_id
        _write_manifest(manifest_path, media, result)

        clip = {
            "media": media,
            "manifest_path": manifest_path,
            "clip_path": clip_path,
            "event_result": result,
            "frames": frames,
            "remaining_post_frames": self.post_event_frames,
        }
        if self.post_event_frames <= 0:
            self._finalize_clip(clip)
        else:
            self.active_clips.append(clip)
        return dict(media)

    def _append_to_active_clips(self, current):
        completed = []
        still_active = []
        for clip in self.active_clips:
            if clip["remaining_post_frames"] > 0:
                clip["frames"].append(FrameSample(_copy_frame(current.frame), current.frame_id, current.timestamp))
                clip["remaining_post_frames"] -= 1
            if clip["remaining_post_frames"] <= 0:
                completed.append(clip)
            else:
                still_active.append(clip)
        self.active_clips = still_active
        return completed

    def _finalize_completed_clips(self, clips):
        for clip in clips:
            self._queue_finalize_clip(clip)

    def _queue_finalize_clip(self, clip):
        try:
            self._finalize_queue.put_nowait(clip)
            self._start_finalize_worker()
        except queue.Full:
            media = clip["media"]
            media["status"] = "finalize_skipped"
            media["error"] = "event media finalize queue full"
            _write_manifest(clip["manifest_path"], media, clip["event_result"])
            logger.warning("Event media finalize queue full; skipped clip event_id=%s", media.get("eventId"))
            self._emit_media_ready(media)

    def _start_finalize_worker(self):
        with self._finalize_lock:
            if self._finalize_thread is not None and self._finalize_thread.is_alive():
                return
            self._finalize_thread = threading.Thread(
                target=self._finalize_loop,
                name="event-media-finalizer",
                daemon=True,
            )
            self._finalize_thread.start()

    def _finalize_loop(self):
        while True:
            try:
                clip = self._finalize_queue.get(timeout=1)
            except queue.Empty:
                with self._finalize_lock:
                    if self._finalize_queue.empty():
                        self._finalize_thread = None
                        return
                    continue
            try:
                self._finalize_clip(clip)
            except Exception as exc:
                media = clip.get("media", {})
                media["status"] = "finalize_failed"
                media["error"] = str(exc)
                try:
                    _write_manifest(clip["manifest_path"], media, clip["event_result"])
                except Exception:
                    logger.exception("Failed to write failed event media manifest")
                logger.exception("Event media finalization failed event_id=%s", media.get("eventId"))
                self._emit_media_ready(media)
            finally:
                self._finalize_queue.task_done()

    def _finalize_clip(self, clip):
        clip_result = _write_video_clip(clip["clip_path"], [sample.frame for sample in clip["frames"]], self.fps)
        media = clip["media"]
        media["status"] = "ready" if clip_result.get("ok") else "frames_saved"
        media["clipFrameCount"] = len(clip["frames"])
        if "frameSequenceDir" in clip_result:
            media["frameSequenceDir"] = clip_result["frameSequenceDir"]
        _write_manifest(clip["manifest_path"], media, clip["event_result"])
        self._emit_media_ready(media)

    def _emit_media_ready(self, media):
        if self.media_ready_callback is None:
            return
        try:
            self.media_ready_callback(dict(media))
        except Exception:
            logger.exception("Event media ready callback failed event_id=%s", media.get("eventId"))

    def _is_in_cooldown(self, event_key, event_seconds):
        if self.cooldown_seconds <= 0:
            return False
        previous = self.last_event_seconds_by_key.get(event_key)
        if previous is None or event_seconds is None:
            return False
        return event_seconds - previous < self.cooldown_seconds


def _is_event_result(result):
    result_type = str(result.get("type", ""))
    if "ALERT" in result_type or "WARNING" in result_type:
        return True
    return result_type == "EMPLOYEE_PRESENCE_EVENT"


def _event_key(result):
    return "|".join(
        str(value)
        for value in (
            result.get("type"),
            result.get("eventType"),
            result.get("trackId"),
            result.get("employeeId"),
            result.get("zoneId"),
        )
    )


def _event_id(current, result, index):
    timestamp = _safe_path_part((current.timestamp or _now()).replace(":", "").replace("+", "_"))
    frame_id = _safe_path_part(str(current.frame_id or "frame"))
    result_type = _safe_path_part(str(result.get("type", "event")).lower())
    return f"{timestamp}_{frame_id}_{index}_{result_type}"


def _write_image(path, frame):
    cv2 = _cv2()
    if cv2.imwrite(str(path), frame) is not True:
        raise RuntimeError(f"Unable to write event keyframe: {path}")


def _write_video_clip(path, frames, fps):
    if not frames:
        return {"ok": False}

    cv2 = _cv2()
    first = frames[0]
    height, width = first.shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if writer.isOpened():
        try:
            for frame in frames:
                writer.write(frame)
            return {"ok": True}
        finally:
            writer.release()

    sequence_dir = path.with_suffix("")
    sequence_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        cv2.imwrite(str(sequence_dir / f"frame_{index:04d}.jpg"), frame)
    return {"ok": False, "frameSequenceDir": str(sequence_dir)}


def _write_manifest(path, media, event_result):
    manifest = {
        "media": media,
        "event": event_result,
        "updatedAt": _now(),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_frame(frame):
    if hasattr(frame, "copy"):
        return frame.copy()
    return frame


def _cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python is required for event media recording. Run `pip install -r requirements.txt` in ai-service."
        ) from exc
    return cv2


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


def _safe_path_part(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "unknown"


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat()
