import subprocess
import threading
import time


class FFmpegStreamWriter:
    """Push OpenCV BGR frames to an RTMP endpoint through FFmpeg."""

    def __init__(self, output_url: str, width: int, height: int, fps: float, ffmpeg_path: str = "ffmpeg"):
        self.output_url = output_url
        self.width = int(width)
        self.height = int(height)
        self.fps = max(1.0, float(fps or 20))
        self.ffmpeg_path = ffmpeg_path
        self.process = None
        self._condition = threading.Condition()
        self._latest_frame = None
        self._stop_event = threading.Event()
        self._writer_thread = None
        self._last_error = None
        self.dropped_frames = 0

    def open(self):
        """Start FFmpeg stdin pipeline."""
        command = [
            self.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{self.width}x{self.height}",
            "-r",
            str(self.fps),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-tune",
            "zerolatency",
            "-bf",
            "0",
            "-g",
            str(max(1, int(round(self.fps * 2)))),
            "-flush_packets",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-f",
            "flv",
            self.output_url,
        ]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self._stop_event.clear()
        self._writer_thread = threading.Thread(target=self._write_loop, name="ffmpeg-stream-writer", daemon=True)
        self._writer_thread.start()
        return self

    def write(self, frame):
        """Queue the latest BGR frame for FFmpeg without blocking processing."""
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("FFmpeg stream writer is not open.")
        if self._last_error is not None:
            raise RuntimeError(self._last_error)
        if self.process.poll() is not None:
            raise RuntimeError(self._ffmpeg_exit_error())
        with self._condition:
            if self._latest_frame is not None:
                self.dropped_frames += 1
            self._latest_frame = frame.copy()
            self._condition.notify()

    def _write_loop(self):
        while not self._stop_event.is_set():
            with self._condition:
                self._condition.wait_for(lambda: self._stop_event.is_set() or self._latest_frame is not None, timeout=0.5)
                if self._stop_event.is_set():
                    break
                frame = self._latest_frame
                self._latest_frame = None
            if frame is None:
                continue
            try:
                if self.process is None or self.process.stdin is None:
                    return
                if self.process.poll() is not None:
                    self._last_error = self._ffmpeg_exit_error()
                    return
                self.process.stdin.write(frame.tobytes())
                self.process.stdin.flush()
            except Exception as exc:
                self._last_error = f"FFmpeg write failed while pushing stream: {exc}"
                return

    def _ffmpeg_exit_error(self):
        stderr_tail = ""
        try:
            if self.process is not None and self.process.stderr is not None:
                stderr_tail = self.process.stderr.read().decode("utf-8", errors="replace")[-1000:]
        except Exception:
            stderr_tail = ""
        detail = f": {stderr_tail.strip()}" if stderr_tail.strip() else ""
        return f"FFmpeg exited while pushing stream: {self.output_url}{detail}"

    def close(self):
        """Close FFmpeg stdin and stop the process."""
        if self.process is None:
            return

        self._stop_event.set()
        with self._condition:
            self._condition.notify_all()
        if self._writer_thread is not None and self._writer_thread.is_alive():
            self._writer_thread.join(timeout=2)
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
            self.process.wait(timeout=5)
        except Exception:
            self.process.kill()
            self.process.wait(timeout=5)
        finally:
            self.process = None

    def __enter__(self):
        return self.open()

    def __exit__(self, _exc_type, _exc, _traceback):
        self.close()
