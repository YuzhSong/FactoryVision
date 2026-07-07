import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_config import Config
from modules.frame_processor import FrameProcessor
from modules.person_detector import PersonDetector
from modules.stream_reader import StreamReader


def main():
    """Check local video reading through the frame processor and YOLO detector."""
    with tempfile.TemporaryDirectory() as temp_dir:
        video_path = Path(temp_dir) / "blank-stream.avi"
        _write_blank_video(video_path)

        detector = PersonDetector(
            model_path=Config.YOLO_MODEL_PATH,
            confidence_threshold=Config.PERSON_CONFIDENCE_THRESHOLD,
            iou_threshold=Config.PERSON_IOU_THRESHOLD,
            device=Config.YOLO_DEVICE,
            image_size=Config.YOLO_IMAGE_SIZE,
            half_precision=Config.YOLO_HALF_PRECISION,
            cudnn_benchmark=Config.YOLO_CUDNN_BENCHMARK,
            track_iou_threshold=Config.PERSON_TRACK_IOU_THRESHOLD,
            max_missed_frames=Config.PERSON_TRACK_MAX_MISSED_FRAMES,
        )
        processor = FrameProcessor(person_detector=detector, face_service=None)
        reader = StreamReader().open_stream(str(video_path))

        reports = []
        try:
            for packet in reader.iter_frames(max_frames=2):
                reports.append(
                    processor.process_frame(
                        packet.frame,
                        camera_id=1,
                        frame_id=packet.frame_id,
                        timestamp=packet.timestamp,
                        include_faces=False,
                        frame_index=packet.frame_index,
                        fps=packet.fps,
                    )
                )
        finally:
            reader.close_stream()

    print(f"processed_frames={len(reports)}")
    print(f"yolo_device={detector.device}")
    print(f"first_frame_id={reports[0]['frameId'] if reports else None}")
    print(f"first_result_count={len(reports[0]['results']) if reports else 0}")


def _write_blank_video(video_path: Path):
    """Write a small blank AVI video for local stream pipeline testing."""
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        5,
        (320, 240),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create test video: {video_path}")

    try:
        for _ in range(3):
            writer.write(np.zeros((240, 320, 3), dtype=np.uint8))
    finally:
        writer.release()


if __name__ == "__main__":
    main()
