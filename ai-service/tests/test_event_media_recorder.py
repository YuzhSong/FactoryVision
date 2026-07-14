import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import numpy as np

from modules.event_media_recorder import EventMediaRecorder


def _frame(value):
    return np.full((32, 32, 3), value, dtype=np.uint8)


def _report(result_type="FALL_ALERT"):
    return {
        "cameraId": 1,
        "frameId": "frame-event",
        "results": [
            {
                "type": result_type,
                "trackId": "t-1",
                "level": "high",
            }
        ],
    }


class EventMediaRecorderTests(unittest.TestCase):
    def test_saves_keyframe_manifest_and_pre_post_clip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = EventMediaRecorder(
                output_dir=tmpdir,
                enabled=True,
                fps=2,
                pre_event_seconds=1,
                post_event_seconds=1,
                cooldown_seconds=0,
            )

            recorder.record_frame(_frame(10), frame_id="frame-1", timestamp="2026-07-08T03:00:00+08:00")
            recorder.record_frame(_frame(20), frame_id="frame-2", timestamp="2026-07-08T03:00:01+08:00")
            media = recorder.record_frame(
                _frame(30),
                frame_id="frame-3",
                timestamp="2026-07-08T03:00:02+08:00",
                report=_report(),
            )
            recorder.record_frame(_frame(40), frame_id="frame-4", timestamp="2026-07-08T03:00:03+08:00")
            recorder.record_frame(_frame(50), frame_id="frame-5", timestamp="2026-07-08T03:00:04+08:00")
            recorder.flush()

            self.assertEqual(len(media), 1)
            self.assertTrue(Path(media[0]["keyframePath"]).exists())
            self.assertTrue(Path(media[0]["manifestPath"]).exists())

            manifest = json.loads(Path(media[0]["manifestPath"]).read_text(encoding="utf-8"))
            manifest_media = manifest["media"]
            self.assertIn(manifest_media["status"], {"ready", "frames_saved"})
            self.assertEqual(manifest_media["clipFrameCount"], 5)
            clip_exists = Path(manifest_media["clipPath"]).exists()
            sequence_exists = (
                "frameSequenceDir" in manifest_media and Path(manifest_media["frameSequenceDir"]).exists()
            )
            self.assertTrue(clip_exists or sequence_exists)
            if clip_exists and shutil.which("ffprobe"):
                probe = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "v:0",
                        "-show_entries",
                        "stream=codec_name,pix_fmt",
                        "-of",
                        "default=nw=1:nk=1",
                        manifest_media["clipPath"],
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertIn("h264", probe.stdout.splitlines())
                self.assertIn("yuv420p", probe.stdout.splitlines())

    def test_cooldown_suppresses_repeated_event_media(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = EventMediaRecorder(
                output_dir=tmpdir,
                enabled=True,
                fps=1,
                pre_event_seconds=0,
                post_event_seconds=0,
                cooldown_seconds=10,
            )

            first = recorder.record_frame(
                _frame(10),
                frame_id="frame-1",
                timestamp="2026-07-08T03:00:00+08:00",
                report=_report("STRANGER_ALERT"),
            )
            second = recorder.record_frame(
                _frame(20),
                frame_id="frame-2",
                timestamp="2026-07-08T03:00:05+08:00",
                report=_report("STRANGER_ALERT"),
            )
            third = recorder.record_frame(
                _frame(30),
                frame_id="frame-3",
                timestamp="2026-07-08T03:00:11+08:00",
                report=_report("STRANGER_ALERT"),
            )
            recorder.flush()

            self.assertEqual(len(first), 1)
            manifest = json.loads(Path(first[0]["manifestPath"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["media"]["preEventFrames"], 0)
            self.assertEqual(second, [])
            self.assertEqual(len(third), 1)


if __name__ == "__main__":
    unittest.main()
