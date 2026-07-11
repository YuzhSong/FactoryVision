import subprocess


class FFmpegStreamWriter:
    """Push OpenCV BGR frames to an RTMP endpoint through FFmpeg."""

    def __init__(self, output_url: str, width: int, height: int, fps: float, ffmpeg_path: str = "ffmpeg"):
        self.output_url = output_url
        self.width = int(width)
        self.height = int(height)
        self.fps = max(1.0, float(fps or 20))
        self.ffmpeg_path = ffmpeg_path
        self.process = None

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
            "veryfast",
            "-tune",
            "zerolatency",
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
            stderr=subprocess.DEVNULL,
        )
        return self

    def write(self, frame):
        """Write one BGR frame to FFmpeg."""
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("FFmpeg stream writer is not open.")
        if self.process.poll() is not None:
            raise RuntimeError(f"FFmpeg exited while pushing stream: {self.output_url}")
        self.process.stdin.write(frame.tobytes())

    def close(self):
        """Close FFmpeg stdin and stop the process."""
        if self.process is None:
            return

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
