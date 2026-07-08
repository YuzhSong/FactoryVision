from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import time
import threading
import traceback

from ai_config import Config
from .event_media_recorder import EventMediaRecorder
from .frame_annotator import FrameAnnotator
from .stream_reader import StreamReader
from .stream_writer import FFmpegStreamWriter


logger = logging.getLogger("uvicorn.error")


@dataclass
class StreamTaskStatus:
    """Current processed-stream task state."""

    camera_id: object | None = None
    input_url: str = Config.STREAM_INPUT_URL
    output_url: str = Config.STREAM_OUTPUT_URL
    play_url: str = Config.STREAM_PLAY_URL
    mode: str = Config.STREAM_PROCESS_MODE
    running: bool = False
    started_at: str | None = None
    stopped_at: str | None = None
    processed_frames: int = 0
    last_frame_id: str | None = None
    last_error: str | None = None
    captured_frames: int = 0
    dropped_frames: int = 0
    capture_fps: float = 0.0
    process_fps: float = 0.0
    process_time_ms: float = 0.0
    latest_frame_age_ms: float = 0.0
    output_fps: float = Config.STREAM_OUTPUT_FPS
    event_media_count: int = 0
    last_event_media: dict | None = None


@dataclass
class LatestFrameSnapshot:
    """Latest captured frame snapshot shared between capture and process loops."""

    packet: object
    sequence: int
    captured_at: float


class ProcessedStreamService:
    """Manage continuous RTMP input -> AI draw -> RTMP output processing."""

    def __init__(
        self,
        frame_processor,
        backend_client=None,
        annotator: FrameAnnotator | None = None,
        default_input_url: str = Config.STREAM_INPUT_URL,
        default_output_url: str = Config.STREAM_OUTPUT_URL,
        default_play_url: str = Config.STREAM_PLAY_URL,
        default_mode: str = Config.STREAM_PROCESS_MODE,
        default_report_to_backend: bool = Config.STREAM_REPORT_TO_BACKEND,
        default_report_realtime_to_backend: bool = Config.STREAM_REPORT_REALTIME_TO_BACKEND,
        reconnect_attempts: int = Config.STREAM_RECONNECT_ATTEMPTS,
        reconnect_delay_seconds: float = Config.STREAM_RECONNECT_DELAY_SECONDS,
        output_fps: float = Config.STREAM_OUTPUT_FPS,
        ffmpeg_path: str = Config.STREAM_FFMPEG_PATH,
        detect_interval: int = Config.FRAME_DETECT_INTERVAL,
        input_width: int = Config.INPUT_WIDTH,
        input_height: int = Config.INPUT_HEIGHT,
        event_media_recorder: EventMediaRecorder | None = None,
        event_media_enabled: bool = Config.EVENT_MEDIA_ENABLED,
        event_media_dir: str = Config.EVENT_MEDIA_DIR,
        event_media_pre_seconds: float = Config.EVENT_MEDIA_PRE_SECONDS,
        event_media_post_seconds: float = Config.EVENT_MEDIA_POST_SECONDS,
        event_media_cooldown_seconds: float = Config.EVENT_MEDIA_COOLDOWN_SECONDS,
    ):
        self.frame_processor = frame_processor
        self.backend_client = backend_client
        self.annotator = annotator or FrameAnnotator()
        self.default_input_url = default_input_url
        self.default_output_url = default_output_url
        self.default_play_url = default_play_url
        self.default_mode = default_mode
        self.default_report_to_backend = default_report_to_backend
        self.default_report_realtime_to_backend = default_report_realtime_to_backend
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.output_fps = output_fps
        self.ffmpeg_path = ffmpeg_path
        self.detect_interval = max(1, int(detect_interval or 1))
        self.input_width = max(0, int(input_width or 0))
        self.input_height = max(0, int(input_height or 0))
        self.event_media_recorder = event_media_recorder or EventMediaRecorder(
            output_dir=event_media_dir,
            enabled=event_media_enabled,
            fps=output_fps or 10.0,
            pre_event_seconds=event_media_pre_seconds,
            post_event_seconds=event_media_post_seconds,
            cooldown_seconds=event_media_cooldown_seconds,
        )
        self._status = StreamTaskStatus(
            input_url=default_input_url,
            output_url=default_output_url,
            play_url=default_play_url,
            mode=default_mode,
            output_fps=output_fps,
        )
        self._thread = None
        self._capture_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._frame_condition = threading.Condition()
        self._latest_frame: LatestFrameSnapshot | None = None
        self._latest_sequence = 0
        self._processed_sequence = 0

    def start(self, payload: dict | None = None):
        """Start background stream processing, or return existing task status."""
        payload = payload or {}
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                snapshot = asdict(self._status)
                return snapshot

            self._stop_event.clear()
            with self._frame_condition:
                self._latest_frame = None
                self._latest_sequence = 0
                self._processed_sequence = 0
            self._status = StreamTaskStatus(
                camera_id=payload.get("cameraId"),
                input_url=payload.get("streamUrl") or payload.get("inputUrl") or self.default_input_url,
                output_url=payload.get("outputUrl") or self.default_output_url,
                play_url=payload.get("playUrl") or self.default_play_url,
                mode=payload.get("mode") or self.default_mode,
                running=True,
                started_at=_now(),
                stopped_at=None,
                processed_frames=0,
                last_frame_id=None,
                last_error=None,
                output_fps=self.output_fps,
                event_media_count=0,
                last_event_media=None,
            )
            if self.event_media_recorder is not None:
                self.event_media_recorder.reset()
            self._thread = threading.Thread(target=self._run, args=(dict(payload),), daemon=True)
            self._thread.start()
            snapshot = asdict(self._status)
        return snapshot

    def stop(self):
        """Request current background stream processing to stop."""
        self._stop_event.set()
        with self._frame_condition:
            self._frame_condition.notify_all()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        capture_thread = self._capture_thread
        if capture_thread is not None and capture_thread.is_alive():
            capture_thread.join(timeout=5)

        with self._lock:
            self._status.running = False
            self._status.stopped_at = self._status.stopped_at or _now()
        return self.status()

    def status(self):
        """Return a JSON-serializable status snapshot."""
        with self._lock:
            return asdict(self._status)

    def _run(self, payload: dict):
        reader = None
        writer = None
        try:
            reader = StreamReader(
                reconnect_attempts=self.reconnect_attempts,
                reconnect_delay_seconds=self.reconnect_delay_seconds,
            ).open_stream(self._status.input_url)

            first_packet = reader.read_frame()
            if first_packet is None:
                raise RuntimeError(f"Unable to read first frame from stream: {self._status.input_url}")

            first_packet = self._prepare_packet(first_packet)
            height, width = first_packet.frame.shape[:2]
            output_fps = self._resolve_output_fps(first_packet.fps)
            with self._lock:
                self._status.output_fps = output_fps

            self._publish_latest_frame(first_packet)
            self._capture_thread = threading.Thread(target=self._capture_loop, args=(reader,), daemon=True)
            self._capture_thread.start()

            writer = FFmpegStreamWriter(
                output_url=self._status.output_url,
                width=width,
                height=height,
                fps=output_fps,
                ffmpeg_path=self.ffmpeg_path,
            ).open()

            self._process_loop(payload, writer, output_fps)
        except Exception as exc:
            with self._lock:
                self._status.last_error = f"{exc}\n{traceback.format_exc(limit=5)}"
            logger.exception("Processed stream task failed")
        finally:
            self._stop_event.set()
            with self._frame_condition:
                self._frame_condition.notify_all()
            if self._capture_thread is not None and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=5)
            if self.event_media_recorder is not None:
                self.event_media_recorder.flush()
            if writer is not None:
                writer.close()
            if reader is not None:
                reader.close_stream()
            with self._lock:
                self._status.running = False
                self._status.stopped_at = _now()

    def _capture_loop(self, reader):
        last_log_at = time.monotonic()
        last_capture_count = 0
        try:
            while not self._stop_event.is_set():
                packet = reader.read_frame()
                if packet is None:
                    break
                self._publish_latest_frame(self._prepare_packet(packet))

                now = time.monotonic()
                if now - last_log_at >= 5:
                    with self._lock:
                        captured_frames = self._status.captured_frames
                        self._status.capture_fps = round((captured_frames - last_capture_count) / (now - last_log_at), 2)
                        capture_fps = self._status.capture_fps
                    last_capture_count = captured_frames
                    last_log_at = now
                    logger.info("capture_fps=%s dropped_frames=%s", capture_fps, self.status()["dropped_frames"])
        except Exception as exc:
            with self._lock:
                self._status.last_error = f"{exc}\n{traceback.format_exc(limit=5)}"
            logger.exception("Capture loop failed")
            self._stop_event.set()
            with self._frame_condition:
                self._frame_condition.notify_all()

    def _process_loop(self, payload: dict, writer, output_fps: float):
        include_faces = _to_bool(payload.get("includeFaces", True))
        report_to_backend = _to_bool(payload.get("reportToBackend", self.default_report_to_backend))
        report_realtime_to_backend = _to_bool(
            payload.get("reportRealtimeToBackend", self.default_report_realtime_to_backend)
        )
        max_frames = _optional_positive_int(payload.get("maxFrames"))
        zones = payload.get("zones") if isinstance(payload.get("zones"), list) else None
        last_report = {"results": []}
        last_log_at = time.monotonic()
        last_process_count = 0
        target_interval = 1 / output_fps if output_fps > 0 else 0

        while not self._stop_event.is_set():
            if max_frames is not None and self._status.processed_frames >= max_frames:
                break

            snapshot = self._wait_for_latest_frame(timeout=1)
            if snapshot is None:
                continue

            started_at = time.monotonic()
            output_frame, last_report = self._process_snapshot(
                snapshot,
                writer,
                include_faces,
                report_to_backend,
                report_realtime_to_backend,
                zones,
                last_report,
            )
            writer.write(output_frame)
            elapsed_ms = (time.monotonic() - started_at) * 1000
            frame_age_ms = (time.monotonic() - snapshot.captured_at) * 1000
            self._mark_processed(snapshot, elapsed_ms, frame_age_ms)

            now = time.monotonic()
            if now - last_log_at >= 5:
                with self._lock:
                    processed_frames = self._status.processed_frames
                    self._status.process_fps = round((processed_frames - last_process_count) / (now - last_log_at), 2)
                    status = asdict(self._status)
                last_process_count = processed_frames
                last_log_at = now
                logger.info(
                    "capture_fps=%s process_fps=%s dropped_frames=%s process_time_ms=%s "
                    "latest_frame_age_ms=%s output_fps=%s",
                    status["capture_fps"],
                    status["process_fps"],
                    status["dropped_frames"],
                    status["process_time_ms"],
                    status["latest_frame_age_ms"],
                    status["output_fps"],
                )

            sleep_for = target_interval - (time.monotonic() - started_at)
            if sleep_for > 0:
                self._stop_event.wait(sleep_for)

    def _process_snapshot(
        self,
        snapshot: LatestFrameSnapshot,
        writer,
        include_faces: bool,
        report_to_backend: bool,
        report_realtime_to_backend: bool,
        zones: list[dict] | None,
        last_report: dict,
    ):
        packet = snapshot.packet
        should_detect = self._should_detect()
        if self._status.mode == "test":
            output_frame = self.annotator.draw_test_box(packet.frame, frame_id=packet.frame_id)
            report = {"results": []}
        elif should_detect:
            report = self.frame_processor.process_frame(
                packet.frame,
                camera_id=self._status.camera_id,
                frame_id=packet.frame_id,
                timestamp=packet.timestamp,
                include_faces=include_faces,
                frame_index=packet.frame_index,
                fps=packet.fps,
                zones=zones,
            )
            output_frame = self.annotator.draw_results(packet.frame, report.get("results", []))
            last_report = report
        else:
            report = last_report or {"results": []}
            output_frame = self.annotator.draw_results(packet.frame, report.get("results", []))

        overlay = self._overlay_metrics(frame_age_ms=(time.monotonic() - snapshot.captured_at) * 1000)
        output_frame = self.annotator.draw_debug_overlay(output_frame, overlay)
        event_media = self._record_event_media(
            output_frame=output_frame,
            packet=packet,
            report=report if should_detect else {"results": []},
        )
        if event_media:
            report["eventMedia"] = list(report.get("eventMedia", [])) + event_media
        if should_detect and report_to_backend and report.get("results") and self.backend_client is not None:
            self.backend_client.report_ai_results(report)
        if should_detect and report_realtime_to_backend and self.backend_client is not None:
            self.backend_client.report_realtime_frame_results(self._with_playback_url(report))
        return output_frame, last_report

    def _publish_latest_frame(self, packet):
        with self._frame_condition:
            self._latest_sequence += 1
            if self._latest_frame is not None and self._latest_sequence - 1 > self._processed_sequence:
                with self._lock:
                    self._status.dropped_frames += 1
            self._latest_frame = LatestFrameSnapshot(
                packet=packet,
                sequence=self._latest_sequence,
                captured_at=time.monotonic(),
            )
            with self._lock:
                self._status.captured_frames += 1
            self._frame_condition.notify()

    def _wait_for_latest_frame(self, timeout: float | None = None):
        with self._frame_condition:
            self._frame_condition.wait_for(
                lambda: self._stop_event.is_set()
                or (self._latest_frame is not None and self._latest_frame.sequence > self._processed_sequence),
                timeout=timeout,
            )
            if self._stop_event.is_set() or self._latest_frame is None:
                return None
            return self._latest_frame

    def _mark_processed(self, snapshot: LatestFrameSnapshot, process_time_ms: float, frame_age_ms: float):
        with self._frame_condition:
            self._processed_sequence = max(self._processed_sequence, snapshot.sequence)
        with self._lock:
            self._status.processed_frames += 1
            self._status.last_frame_id = snapshot.packet.frame_id
            self._status.process_time_ms = round(process_time_ms, 2)
            self._status.latest_frame_age_ms = round(frame_age_ms, 2)

    def _record_event_media(self, output_frame, packet, report):
        if self.event_media_recorder is None:
            return []

        event_media = self.event_media_recorder.record_frame(
            output_frame,
            frame_id=packet.frame_id,
            timestamp=packet.timestamp,
            report=report,
        )
        if event_media:
            with self._lock:
                self._status.event_media_count += len(event_media)
                self._status.last_event_media = event_media[-1]
        return event_media

    def _prepare_packet(self, packet):
        if not self.input_width or not self.input_height:
            return packet
        try:
            import cv2
        except ImportError:
            return packet

        packet.frame = cv2.resize(packet.frame, (self.input_width, self.input_height))
        return packet

    def _should_detect(self):
        if self.detect_interval <= 1:
            return True
        return self._status.processed_frames % self.detect_interval == 0

    def _overlay_metrics(self, frame_age_ms: float):
        with self._lock:
            return {
                "time": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "process_fps": self._status.process_fps,
                "dropped_frames": self._status.dropped_frames,
                "frame_age_ms": round(frame_age_ms, 2),
                "playback_mode": "detected stream",
            }

    def _resolve_output_fps(self, input_fps):
        if self.output_fps > 0:
            return self.output_fps
        return input_fps or 20

    def _with_playback_url(self, report):
        payload = dict(report)
        if self._status.play_url:
            payload["playbackUrl"] = self._status.play_url
        return payload


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat()


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _optional_positive_int(value):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
