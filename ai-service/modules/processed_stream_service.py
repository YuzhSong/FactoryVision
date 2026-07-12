from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import queue
import time
import threading
import traceback
from collections import deque

from ai_config import Config
from .event_media_recorder import EventMediaRecorder
from .frame_annotator import FrameAnnotator
from .stream_reader import StreamReader
from .stream_writer import FFmpegStreamWriter
from .event_types import normalize_event_result


logger = logging.getLogger("uvicorn.error")
FIXED_CAMERA_ROTATION = 270


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
    input_fps: float = 0.0
    actual_output_fps: float = 0.0
    event_media_count: int = 0
    last_event_media: dict | None = None
    input_frame_shape: list[int] | None = None
    normalized_frame_shape: list[int] | None = None
    output_frame_size: list[int] | None = None
    queued_events: int = 0
    reported_events: int = 0
    failed_events: int = 0
    dropped_events: int = 0
    filtered_results: int = 0
    last_report_error: str | None = None
    last_report_succeeded_at: str | None = None
    last_report_attempted_at: str | None = None
    last_report_response: dict | None = None
    person_inference_ms: float | None = None
    helmet_inference_ms: float | None = None
    face_inference_ms: float | None = None
    last_person_frame_id: str | None = None
    last_helmet_frame_id: str | None = None
    last_face_frame_id: str | None = None
    timing_summary_ms: dict | None = None
    active_config: dict | None = None


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
        reconnect_attempts: int = Config.STREAM_RECONNECT_ATTEMPTS,
        reconnect_delay_seconds: float = Config.STREAM_RECONNECT_DELAY_SECONDS,
        output_fps: float = Config.STREAM_OUTPUT_FPS,
        ffmpeg_path: str = Config.STREAM_FFMPEG_PATH,
        detect_interval: int = Config.FRAME_DETECT_INTERVAL,
        person_detect_interval: int = Config.PERSON_DETECT_INTERVAL,
        helmet_detect_interval: int = Config.HELMET_DETECT_INTERVAL,
        helmet_detect_offset: int = Config.HELMET_DETECT_OFFSET,
        face_detect_interval: int = Config.FACE_DETECT_INTERVAL,
        face_detect_offset: int = Config.FACE_DETECT_OFFSET,
        detection_cache_max_age_frames: int = Config.DETECTION_CACHE_MAX_AGE_FRAMES,
        input_width: int = Config.INPUT_WIDTH,
        input_height: int = Config.INPUT_HEIGHT,
        event_media_recorder: EventMediaRecorder | None = None,
        event_media_enabled: bool = Config.EVENT_MEDIA_ENABLED,
        event_media_dir: str = Config.EVENT_MEDIA_DIR,
        event_media_pre_seconds: float = Config.EVENT_MEDIA_PRE_SECONDS,
        event_media_post_seconds: float = Config.EVENT_MEDIA_POST_SECONDS,
        event_media_cooldown_seconds: float = Config.EVENT_MEDIA_COOLDOWN_SECONDS,
        event_report_queue_size: int = Config.EVENT_REPORT_QUEUE_SIZE,
        zone_refresh_interval_seconds: float = Config.ZONE_REFRESH_INTERVAL_SECONDS,
    ):
        self.frame_processor = frame_processor
        self.backend_client = backend_client
        self.annotator = annotator or FrameAnnotator()
        self.default_input_url = default_input_url
        self.default_output_url = default_output_url
        self.default_play_url = default_play_url
        self.default_mode = default_mode
        self.default_report_to_backend = default_report_to_backend
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.output_fps = output_fps
        self.ffmpeg_path = ffmpeg_path
        self.detect_interval = max(1, int(detect_interval or 1))
        self.person_detect_interval = max(1, int(person_detect_interval or 1))
        self.helmet_detect_interval = max(1, int(helmet_detect_interval or 1))
        self.helmet_detect_offset = max(0, int(helmet_detect_offset or 0))
        self.face_detect_interval = max(1, int(face_detect_interval or 1))
        self.face_detect_offset = max(0, int(face_detect_offset or 0))
        self.detection_cache_max_age_frames = max(1, int(detection_cache_max_age_frames or 1))
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
        self._event_report_queue = queue.Queue(maxsize=max(1, int(event_report_queue_size or 1)))
        self.zone_refresh_interval_seconds = max(1.0, float(zone_refresh_interval_seconds or 1))
        self._event_report_stop = threading.Event()
        self._event_report_lock = threading.Lock()
        self._report_thread = None
        self._queued_region_event_keys = set()
        self._latest_frame: LatestFrameSnapshot | None = None
        self._latest_sequence = 0
        self._processed_sequence = 0
        self._cached_person_detections = []
        self._cached_helmet_detections = []
        self._person_cache_frame = None
        self._helmet_cache_frame = None
        self._timing_samples = {
            name: deque(maxlen=300)
            for name in ("person", "helmet", "face", "zoneRules", "draw", "encode", "overall")
        }
        self._frame_age_samples = deque(maxlen=120)
        self._schedule_frames = {name: deque(maxlen=20) for name in ("person", "helmet", "face")}
        self._last_face_due_frame = -1

    def start(self, payload: dict | None = None):
        """Start background stream processing, or return existing task status."""
        payload = dict(payload or {})
        if _to_bool(payload.get("reportRealtimeToBackend")):
            raise ValueError("`reportRealtimeToBackend` is no longer supported; use `reportToBackend`.")
        input_url = payload.get("inputUrl") or payload.get("streamUrl") or self.default_input_url
        if not input_url:
            raise ValueError("`inputUrl` is required.")
        payload["inputUrl"] = input_url
        run_config = self._resolve_run_config(payload)
        if run_config["reportToBackend"] and not payload.get("cameraId"):
            raise ValueError("`cameraId` is required when `reportToBackend` is enabled.")
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                snapshot = asdict(self._status)
                return snapshot

            self._stop_event.clear()
            self._event_report_stop.clear()
            self._cached_person_detections = []
            self._cached_helmet_detections = []
            self._person_cache_frame = None
            self._helmet_cache_frame = None
            for samples in self._timing_samples.values():
                samples.clear()
            self._frame_age_samples.clear()
            for frames in self._schedule_frames.values():
                frames.clear()
            self._last_face_due_frame = -1
            with self._frame_condition:
                self._latest_frame = None
                self._latest_sequence = 0
                self._processed_sequence = 0
            self._status = StreamTaskStatus(
                camera_id=payload.get("cameraId"),
                input_url=input_url,
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
                active_config=run_config,
            )
            if self.event_media_recorder is not None:
                self.event_media_recorder.reset()
            self._thread = threading.Thread(target=self._run, args=(payload, run_config), daemon=True)
            self._thread.start()
            snapshot = asdict(self._status)
        return snapshot

    def _resolve_run_config(self, payload: dict) -> dict:
        """Freeze the resolved start payload so all worker threads use one configuration."""
        return {
            "configVersion": payload.get("configVersion"),
            "includeFaces": _to_bool(payload.get("includeFaces", Config.STREAM_INCLUDE_FACES_DEFAULT)),
            "reportToBackend": _to_bool(payload.get("reportToBackend", self.default_report_to_backend)),
            "personDetectInterval": _positive_int(payload.get("personDetectInterval"), self.person_detect_interval),
            "helmetDetectInterval": _positive_int(payload.get("helmetDetectInterval"), self.helmet_detect_interval),
            "helmetDetectOffset": _non_negative_int(payload.get("helmetDetectOffset"), self.helmet_detect_offset),
            "faceDetectInterval": _positive_int(payload.get("faceDetectInterval"), self.face_detect_interval),
            "faceDetectOffset": _non_negative_int(payload.get("faceDetectOffset"), self.face_detect_offset),
            "zoneRefreshIntervalSeconds": _positive_float(payload.get("zoneRefreshIntervalSeconds"), self.zone_refresh_interval_seconds),
            "reconnectAttempts": _positive_int(payload.get("reconnectAttempts"), self.reconnect_attempts),
            "reconnectDelaySeconds": _positive_float(payload.get("reconnectDelaySeconds"), self.reconnect_delay_seconds),
        }

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
        self._shutdown_report_worker()

        with self._lock:
            self._status.running = False
            self._status.stopped_at = self._status.stopped_at or _now()
        return self.status()

    def status(self):
        """Return a JSON-serializable status snapshot."""
        with self._lock:
            snapshot = asdict(self._status)
            snapshot["pending_events"] = self._event_report_queue.qsize()
            snapshot["filtered_events"] = snapshot["filtered_results"]
            snapshot["timing_summary_ms"] = {
                name: _timing_summary(samples) for name, samples in self._timing_samples.items()
            }
            snapshot["latest_frame_age_avg_2s_ms"] = _recent_average(
                self._frame_age_samples,
                window_seconds=2.0,
                fallback=self._status.latest_frame_age_ms,
            )
            snapshot["model_schedule_frames"] = {
                name: list(frames) for name, frames in self._schedule_frames.items()
            }
            return snapshot

    def _run(self, payload: dict, run_config: dict):
        reader = None
        writer = None
        try:
            reader = StreamReader(
                reconnect_attempts=run_config["reconnectAttempts"],
                reconnect_delay_seconds=run_config["reconnectDelaySeconds"],
            ).open_stream(self._status.input_url)

            first_packet = reader.read_frame()
            if first_packet is None:
                raise RuntimeError(f"Unable to read first frame from stream: {self._status.input_url}")

            first_packet = self._prepare_packet(first_packet)
            height, width = first_packet.frame.shape[:2]
            output_fps = self._resolve_output_fps(first_packet.fps)
            with self._lock:
                self._status.output_fps = output_fps
                self._status.input_fps = round(float(first_packet.fps or 0), 2)
                self._status.output_frame_size = [width, height]

            logger.info(
                "fixed_camera_mode rotation=270 input_shape=%s normalized_shape=%s output_size=%sx%s",
                self._status.input_frame_shape,
                self._status.normalized_frame_shape,
                width,
                height,
            )

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

            self._process_loop(payload, writer, output_fps, run_config)
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
            self._shutdown_report_worker()
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

    def _process_loop(self, payload: dict, writer, output_fps: float, run_config: dict):
        include_faces = run_config["includeFaces"]
        report_to_backend = run_config["reportToBackend"]
        max_frames = _optional_positive_int(payload.get("maxFrames"))
        zones = payload.get("zones") if isinstance(payload.get("zones"), list) else None
        zones_last_refreshed_at = time.monotonic()
        last_report = {"results": []}
        last_log_at = time.monotonic()
        last_process_count = 0
        target_interval = 1 / output_fps if output_fps > 0 else 0

        while not self._stop_event.is_set():
            if (
                self.backend_client is not None
                and self._status.camera_id
                and time.monotonic() - zones_last_refreshed_at >= run_config["zoneRefreshIntervalSeconds"]
            ):
                try:
                    zones = self.backend_client.list_zones(self._status.camera_id)
                    zones_last_refreshed_at = time.monotonic()
                except Exception as exc:
                    logger.warning("zone refresh failed camera_id=%s error=%s", self._status.camera_id, exc)
                    zones_last_refreshed_at = time.monotonic()
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
                zones,
                last_report,
                run_config,
            )
            encode_started_at = time.perf_counter()
            writer.write(output_frame)
            encode_ms = (time.perf_counter() - encode_started_at) * 1000
            self._record_timing("encode", encode_ms)
            elapsed_ms = (time.monotonic() - started_at) * 1000
            frame_age_ms = (time.monotonic() - snapshot.captured_at) * 1000
            self._mark_processed(snapshot, elapsed_ms, frame_age_ms)

            now = time.monotonic()
            if now - last_log_at >= 5:
                with self._lock:
                    processed_frames = self._status.processed_frames
                    self._status.process_fps = round((processed_frames - last_process_count) / (now - last_log_at), 2)
                    self._status.actual_output_fps = self._status.process_fps
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
        zones: list[dict] | None,
        last_report: dict,
        run_config: dict | None = None,
    ):
        packet = snapshot.packet
        model_runs = self._model_runs(include_faces, run_config)
        should_detect = any(model_runs.values())
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
                person_detections=self._cached_people_for_frame(),
                helmet_detections=self._cached_helmets_for_frame(),
                run_person_detection=model_runs["person"],
                run_helmet_detection=model_runs["helmet"],
                run_face_recognition=model_runs["face"],
            )
            self._update_detection_cache(report)
            self._record_model_metrics(report, packet.frame_id)
            draw_started_at = time.perf_counter()
            output_frame = self._draw_detection_frame(packet.frame, zones, report.get("results", []))
            self._record_timing("draw", (time.perf_counter() - draw_started_at) * 1000)
            last_report = report
        else:
            report = last_report or {"results": []}
            draw_started_at = time.perf_counter()
            output_frame = self._draw_detection_frame(packet.frame, zones, report.get("results", []))
            self._record_timing("draw", (time.perf_counter() - draw_started_at) * 1000)

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
            reportable = self._reportable_event_report(report)
            if reportable["results"]:
                logger.info(
                    "event generated camera_id=%s types=%s",
                    reportable.get("cameraId"),
                    [item.get("eventType") or item.get("type") for item in reportable["results"]],
                )
                self._enqueue_ai_report(reportable)
        return output_frame, last_report

    def _draw_detection_frame(self, frame, zones, results):
        """Keep custom test annotators compatible while rendering regions before boxes."""
        output = self.annotator.draw_zones(frame, zones, results) if hasattr(self.annotator, "draw_zones") else frame
        return self.annotator.draw_results(output, results)

    def _enqueue_ai_report(self, report):
        """Queue reports FIFO without blocking frame processing or overwriting safety events."""
        payload = dict(report)
        payload["results"] = list(report.get("results") or [])
        event_keys = _region_event_keys(payload)
        with self._event_report_lock:
            duplicate_keys = event_keys & self._queued_region_event_keys
            if duplicate_keys:
                payload["results"] = [
                    result for result in payload["results"]
                    if _region_event_key(result) not in duplicate_keys
                ]
                event_keys -= duplicate_keys
            if not payload["results"]:
                return False
            try:
                self._event_report_queue.put_nowait((payload, event_keys))
            except queue.Full:
                dropped = len(payload["results"])
                with self._lock:
                    self._status.dropped_events += dropped
                logger.error(
                    "AI report queue full (capacity=%s); dropped_events=%s",
                    self._event_report_queue.maxsize,
                    dropped,
                )
                return False
            self._queued_region_event_keys.update(event_keys)
            with self._lock:
                self._status.queued_events += len(payload["results"])
            logger.info("event queued camera_id=%s count=%s", payload.get("cameraId"), len(payload["results"]))
            self._start_report_worker_locked()
        return True

    def _reportable_event_report(self, report):
        """Keep raw detections in the video path but persist only actionable events."""
        allowed_types = {
            "HELMET_WARNING",
            "ZONE_WARNING",
            "RUNNING_ALERT",
            "STRANGER_DETECTED",
            "STRANGER_ALERT",
            "FACE_RECOGNIZED",
        }
        payload = dict(report)
        source_results = report.get("results") or []
        payload["results"] = [
            normalize_event_result(result)
            for result in source_results
            if isinstance(result, dict)
            and result.get("type") in allowed_types
        ]
        with self._lock:
            self._status.filtered_results += max(0, len(source_results) - len(payload["results"]))
        return payload

    def _start_report_worker_locked(self):
        if self._report_thread is not None and self._report_thread.is_alive():
            return
        self._report_thread = threading.Thread(target=self._report_loop, name="ai-result-reporter", daemon=True)
        self._report_thread.start()

    def _report_loop(self):
        while not self._event_report_stop.is_set() or not self._event_report_queue.empty():
            try:
                report, event_keys = self._event_report_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                with self._lock:
                    self._status.last_report_attempted_at = _now()
                response = self.backend_client.report_ai_results(report)
                with self._lock:
                    self._status.reported_events += len(report.get("results") or [])
                    self._status.last_report_succeeded_at = _now()
                    self._status.last_report_error = None
                    self._status.last_report_response = response.get("data", response) if isinstance(response, dict) else None
                logger.info("event report succeeded camera_id=%s count=%s", report.get("cameraId"), len(report.get("results") or []))
            except Exception as exc:
                with self._lock:
                    self._status.failed_events += len(report.get("results") or [])
                    self._status.last_report_error = str(exc)
                logger.exception("AI result report failed without blocking video processing: %s", exc)
            finally:
                with self._event_report_lock:
                    self._queued_region_event_keys.difference_update(event_keys)
                self._event_report_queue.task_done()

    def _shutdown_report_worker(self):
        self._event_report_stop.set()
        report_thread = self._report_thread
        if report_thread is not None and report_thread.is_alive():
            report_thread.join(timeout=5)

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
            self._frame_age_samples.append((time.monotonic(), float(frame_age_ms)))
        self._record_timing("overall", process_time_ms)

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
        try:
            import cv2
        except ImportError:
            return packet

        original_shape = list(packet.frame.shape[:2])
        frame = normalize_camera_frame(packet.frame)
        normalized_shape = list(frame.shape[:2])
        if self.input_width and self.input_height:
            frame = _resize_landscape_frame(frame, self.input_width, self.input_height, cv2)
        packet.frame = frame
        output_height, output_width = frame.shape[:2]
        with self._lock:
            self._status.input_frame_shape = original_shape
            self._status.normalized_frame_shape = normalized_shape
            self._status.output_frame_size = [output_width, output_height]
        return packet

    def _should_detect(self):
        """Keep the legacy interval helper available for callers and tests."""
        if self.detect_interval <= 1:
            return True
        return self._status.processed_frames % self.detect_interval == 0

    def _model_runs(self, include_faces: bool, run_config: dict | None = None):
        """Schedule one model per tick while retaining the legacy analysis cadence."""
        run_config = run_config or {}
        frame_number = self._status.processed_frames
        person_interval = _positive_int(run_config.get("personDetectInterval"), self.person_detect_interval)
        helmet_interval = _positive_int(run_config.get("helmetDetectInterval"), self.helmet_detect_interval)
        helmet_offset = _non_negative_int(run_config.get("helmetDetectOffset"), self.helmet_detect_offset)
        face_interval = _positive_int(run_config.get("faceDetectInterval"), self.face_detect_interval)
        face_offset = _non_negative_int(run_config.get("faceDetectOffset"), self.face_detect_offset)
        person = self._should_run_interval(frame_number, person_interval)
        helmet_due = self._should_run_interval(
            frame_number,
            helmet_interval,
            helmet_offset,
        )
        helmet_deferred = (
            frame_number > 0
            and self._should_run_interval(frame_number - 1, helmet_interval, helmet_offset)
            and self._should_run_interval(frame_number - 1, person_interval)
        )
        helmet = not person and (helmet_due or helmet_deferred)
        face_due_frame = _latest_due_frame(frame_number, face_interval, face_offset)
        face = bool(
            include_faces
            and not person
            and not helmet
            and face_due_frame is not None
            and face_due_frame > self._last_face_due_frame
        )
        if face:
            self._last_face_due_frame = face_due_frame
        return {
            "person": person,
            "helmet": helmet,
            "face": face,
        }

    @staticmethod
    def _should_run_interval(frame_number: int, interval: int, offset: int = 0):
        return (frame_number - offset) >= 0 and (frame_number - offset) % interval == 0

    def _cached_people_for_frame(self):
        if not self._cache_is_fresh(self._person_cache_frame):
            return []
        return [dict(item) for item in self._cached_person_detections]

    def _cached_helmets_for_frame(self):
        if not self._cache_is_fresh(self._helmet_cache_frame):
            return []
        return [dict(item) for item in self._cached_helmet_detections]

    def _cache_is_fresh(self, cache_frame):
        return cache_frame is not None and self._status.processed_frames - cache_frame <= self.detection_cache_max_age_frames

    def _update_detection_cache(self, report):
        results = report.get("results") or []
        if report.get("modelRuns", {}).get("person"):
            self._cached_person_detections = [
                dict(result) for result in results if result.get("type") == "PERSON_DETECTION"
            ]
            self._person_cache_frame = self._status.processed_frames
        if report.get("modelRuns", {}).get("helmet"):
            self._cached_helmet_detections = [
                dict(result) for result in results if result.get("type") == "HELMET_DETECTION"
            ]
            self._helmet_cache_frame = self._status.processed_frames

    def _record_model_metrics(self, report, frame_id):
        timings = report.get("modelTimingsMs") or {}
        model_runs = report.get("modelRuns") or {}
        with self._lock:
            if model_runs.get("person"):
                self._status.person_inference_ms = timings.get("person")
                self._status.last_person_frame_id = frame_id
                self._schedule_frames["person"].append(self._status.processed_frames)
            if model_runs.get("helmet"):
                self._status.helmet_inference_ms = timings.get("helmet")
                self._status.last_helmet_frame_id = frame_id
                self._schedule_frames["helmet"].append(self._status.processed_frames)
            if model_runs.get("face"):
                self._status.face_inference_ms = timings.get("face")
                self._status.last_face_frame_id = frame_id
                self._schedule_frames["face"].append(self._status.processed_frames)
        for name in ("person", "helmet", "face", "zoneRules"):
            if name in timings:
                self._record_timing(name, timings[name])

    def _record_timing(self, name, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return
        with self._lock:
            samples = self._timing_samples.get(name)
            if samples is not None:
                samples.append(number)

    def _overlay_metrics(self, frame_age_ms: float):
        with self._lock:
            return {
                "time": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                "process_fps": self._status.process_fps,
                "dropped_frames": self._status.dropped_frames,
                "frame_age_ms": round(frame_age_ms, 2),
                "frame_age_avg_2s_ms": _recent_average(
                    self._frame_age_samples,
                    window_seconds=2.0,
                    fallback=frame_age_ms,
                ),
                "playback_mode": "detected stream",
                "rotation": FIXED_CAMERA_ROTATION,
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


def normalize_camera_frame(frame):
    try:
        import cv2
    except ImportError:
        return frame
    return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)


def _resize_landscape_frame(frame, target_width: int, target_height: int, cv2_module):
    source_height, source_width = frame.shape[:2]
    if source_width <= 0 or source_height <= 0:
        return frame

    scale = min(target_width / source_width, target_height / source_height)
    if scale <= 0:
        return frame

    resized_width = _ensure_even(max(2, int(round(source_width * scale))))
    resized_height = _ensure_even(max(2, int(round(source_height * scale))))
    return cv2_module.resize(frame, (resized_width, resized_height))


def _ensure_even(value: int):
    return value if value % 2 == 0 else max(2, value - 1)


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


def _positive_int(value, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return max(1, int(default))


def _non_negative_int(value, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return max(0, int(default))


def _positive_float(value, default: float) -> float:
    try:
        return max(0.01, float(value))
    except (TypeError, ValueError):
        return max(0.01, float(default))


def _region_event_keys(report):
    return {key for key in (_region_event_key(result) for result in report.get("results") or []) if key is not None}


def _region_event_key(result):
    if not isinstance(result, dict) or result.get("eventType") not in {"region_intrusion", "region_dwell"}:
        return None
    return (
        str(result.get("cameraId")),
        str(result.get("regionId")),
        str(result.get("trackId")),
        str(result.get("eventType")),
        str(result.get("enteredAt")),
    )


def _timing_summary(samples):
    values = sorted(float(value) for value in samples)
    if not values:
        return {"count": 0, "average": None, "p95": None, "max": None}
    index = min(len(values) - 1, max(0, int((len(values) * 0.95) + 0.999999) - 1))
    return {
        "count": len(values),
        "average": round(sum(values) / len(values), 2),
        "p95": round(values[index], 2),
        "max": round(values[-1], 2),
    }


def _recent_average(samples, window_seconds: float, fallback=None):
    now = time.monotonic()
    values = [float(value) for recorded_at, value in samples if now - float(recorded_at) <= window_seconds]
    if not values:
        return round(float(fallback), 2) if fallback is not None else None
    return round(sum(values) / len(values), 2)


def _latest_due_frame(frame_number, interval, offset):
    if frame_number < offset:
        return None
    return frame_number - ((frame_number - offset) % interval)
