from dataclasses import dataclass
from datetime import datetime, timezone
import time


@dataclass
class FramePacket:
    frame: object
    frame_id: str
    frame_index: int
    timestamp: str
    fps: float | None = None


class StreamReader:
    def __init__(self, reconnect_attempts: int = 3, reconnect_delay_seconds: float = 1.0):
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.stream_url = None
        self.capture = None
        self.frame_index = 0
        self.fps = None

    def open_stream(self, stream_url: str):
        self.close_stream()
        self.stream_url = stream_url
        self.frame_index = 0
        self.capture = self._open_capture(stream_url)
        self.fps = self._read_fps()
        return self

    def read_frame(self):
        if self.capture is None or not self.capture.isOpened():
            self._reconnect()

        for attempt in range(self.reconnect_attempts + 1):
            success, frame = self.capture.read()
            if success and frame is not None:
                self.frame_index += 1
                return FramePacket(
                    frame=frame,
                    frame_id=f"frame-{self.frame_index:06d}",
                    frame_index=self.frame_index,
                    timestamp=datetime.now(timezone.utc).astimezone().isoformat(),
                    fps=self.fps,
                )

            if attempt >= self.reconnect_attempts:
                return None

            self._reconnect()

        return None

    def iter_frames(self, max_frames: int | None = None, sample_interval: int = 1):
        emitted = 0
        sample_interval = max(1, int(sample_interval or 1))

        while max_frames is None or emitted < max_frames:
            packet = self.read_frame()
            if packet is None:
                break

            if packet.frame_index % sample_interval != 0:
                continue

            emitted += 1
            yield packet

    def close_stream(self):
        if self.capture is not None:
            self.capture.release()
        self.capture = None

    def _open_capture(self, stream_url):
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "opencv-python is required for video stream reading. Run `pip install -r requirements.txt` in ai-service."
            ) from exc

        source = _coerce_source(stream_url)
        capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Unable to open video stream: {stream_url}")
        return capture

    def _reconnect(self):
        if not self.stream_url:
            raise RuntimeError("Stream URL is not configured.")

        self.close_stream()
        last_error = None
        for _attempt in range(self.reconnect_attempts):
            try:
                if self.reconnect_delay_seconds > 0:
                    time.sleep(self.reconnect_delay_seconds)
                self.capture = self._open_capture(self.stream_url)
                self.fps = self._read_fps()
                return
            except RuntimeError as exc:
                last_error = exc

        raise RuntimeError(f"Unable to reconnect video stream: {self.stream_url}") from last_error

    def _read_fps(self):
        if self.capture is None:
            return None

        try:
            import cv2

            fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 0)
        except Exception:
            return None

        return fps if fps > 0 else None

    def __enter__(self):
        if self.stream_url is None:
            raise RuntimeError("Call open_stream before entering StreamReader context.")
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        self.close_stream()


def _coerce_source(stream_url):
    if isinstance(stream_url, int):
        return stream_url

    if isinstance(stream_url, str) and stream_url.isdigit():
        return int(stream_url)

    return stream_url
