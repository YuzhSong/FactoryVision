from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import threading
import traceback

from ai_config import Config
from .frame_annotator import FrameAnnotator
from .stream_reader import StreamReader
from .stream_writer import FFmpegStreamWriter


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
        self._status = StreamTaskStatus(
            input_url=default_input_url,
            output_url=default_output_url,
            play_url=default_play_url,
            mode=default_mode,
        )
        self._thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self, payload: dict | None = None):
        """Start background stream processing, or return existing task status."""
        payload = payload or {}
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                snapshot = asdict(self._status)
                return snapshot

            self._stop_event.clear()
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
            )
            self._thread = threading.Thread(target=self._run, args=(dict(payload),), daemon=True)
            self._thread.start()
            snapshot = asdict(self._status)
        return snapshot

    def stop(self):
        """Request current background stream processing to stop."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)

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
            include_faces = _to_bool(payload.get("includeFaces", True))
            report_to_backend = _to_bool(payload.get("reportToBackend", self.default_report_to_backend))
            max_frames = _optional_positive_int(payload.get("maxFrames"))
            zones = payload.get("zones") if isinstance(payload.get("zones"), list) else None

            reader = StreamReader(
                reconnect_attempts=self.reconnect_attempts,
                reconnect_delay_seconds=self.reconnect_delay_seconds,
            ).open_stream(self._status.input_url)

            first_packet = reader.read_frame()
            if first_packet is None:
                raise RuntimeError(f"Unable to read first frame from stream: {self._status.input_url}")

            height, width = first_packet.frame.shape[:2]
            output_fps = self._resolve_output_fps(first_packet.fps)
            writer = FFmpegStreamWriter(
                output_url=self._status.output_url,
                width=width,
                height=height,
                fps=output_fps,
                ffmpeg_path=self.ffmpeg_path,
            ).open()

            self._process_packet(first_packet, writer, include_faces, report_to_backend, zones)

            while not self._stop_event.is_set():
                if max_frames is not None and self._status.processed_frames >= max_frames:
                    break

                packet = reader.read_frame()
                if packet is None:
                    break
                self._process_packet(packet, writer, include_faces, report_to_backend, zones)
        except Exception as exc:
            with self._lock:
                self._status.last_error = f"{exc}\n{traceback.format_exc(limit=5)}"
        finally:
            if writer is not None:
                writer.close()
            if reader is not None:
                reader.close_stream()
            with self._lock:
                self._status.running = False
                self._status.stopped_at = _now()

    def _process_packet(self, packet, writer, include_faces: bool, report_to_backend: bool, zones: list[dict] | None):
        if self._status.mode == "test":
            output_frame = self.annotator.draw_test_box(packet.frame, frame_id=packet.frame_id)
            report = {"results": []}
        else:
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

        writer.write(output_frame)
        if report_to_backend and report.get("results") and self.backend_client is not None:
            self.backend_client.report_ai_results(report)

        with self._lock:
            self._status.processed_frames += 1
            self._status.last_frame_id = packet.frame_id

    def _resolve_output_fps(self, input_fps):
        if self.output_fps > 0:
            return self.output_fps
        return input_fps or 20


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
