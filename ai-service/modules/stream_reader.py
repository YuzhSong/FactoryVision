from dataclasses import dataclass
from datetime import datetime, timezone
import os
import time


@dataclass
class FramePacket:
    """Carry one decoded video frame with frame metadata."""

    frame: object
    frame_id: str
    frame_index: int
    timestamp: str
    fps: float | None = None


class StreamReader:
    """Read frames from local video, camera index, or stream URL with OpenCV."""

    def __init__(self, reconnect_attempts: int = 3, reconnect_delay_seconds: float = 1.0):
        """Initialize stream reader with reconnect controls."""
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.stream_url = None
        self.capture = None
        self.frame_index = 0
        self.fps = None

    def open_stream(self, stream_url: str):
        """Open video source by stream_url or camera index."""
        self.close_stream()
        self.stream_url = stream_url
        self.frame_index = 0
        self.capture = self._open_capture(stream_url)
        self.fps = self._read_fps()
        return self

    def read_frame(self):
        """Read one frame and return FramePacket, or None at end/failure."""
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
        """Yield sampled FramePacket objects up to max_frames."""
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
        """Release current OpenCV capture if open."""
        if self.capture is not None:
            self.capture.release()
        self.capture = None

    def _open_capture(self, stream_url):
        """Create OpenCV VideoCapture for the given source."""
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError(
                "opencv-python is required for video stream reading. Run `pip install -r requirements.txt` in ai-service."
            ) from exc

        source = _coerce_source(stream_url)
        capture = self._video_capture(cv2, source, low_latency=True)
        if not capture.isOpened() and isinstance(source, str) and "://" in source:
            capture.release()
            capture = self._video_capture(cv2, source, low_latency=False)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Unable to open video stream: {stream_url}")
        try:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return capture

    def _video_capture(self, cv2, source, low_latency: bool):
        previous_options = os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS")
        try:
            if low_latency and isinstance(source, str) and "://" in source:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                    "fflags;nobuffer|flags;low_delay|probesize;32|analyzeduration;0"
                )
            elif previous_options is None:
                os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
            return cv2.VideoCapture(source)
        finally:
            if previous_options is None:
                os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = previous_options

    def _reconnect(self):
        """Reconnect to the configured stream_url."""
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
        """Read FPS from current capture when available."""
        if self.capture is None:
            return None

        try:
            import cv2

            fps = float(self.capture.get(cv2.CAP_PROP_FPS) or 0)
        except Exception:
            return None

        return fps if fps > 0 else None

    def __enter__(self):
        """Enter context after stream has been opened."""
        if self.stream_url is None:
            raise RuntimeError("Call open_stream before entering StreamReader context.")
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        """Close stream when leaving context manager."""
        self.close_stream()


def _coerce_source(stream_url):
    """Convert numeric camera source strings to int for OpenCV."""
    if isinstance(stream_url, int):
        return stream_url

    if isinstance(stream_url, str) and stream_url.isdigit():
        return int(stream_url)

    return stream_url
