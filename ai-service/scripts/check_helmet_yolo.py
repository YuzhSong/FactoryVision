import argparse
import sys
from pathlib import Path

import numpy as np


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai_config import Config
from modules.helmet_detector import HelmetDetector


def parse_args():
    """Parse optional image path for helmet YOLO smoke testing."""
    parser = argparse.ArgumentParser(description="Check helmet YOLO model loading and inference.")
    parser.add_argument(
        "--provider",
        choices=["opensource", "self_trained"],
        default=Config.HELMET_MODEL_PROVIDER,
        help="Helmet model provider strategy.",
    )
    parser.add_argument("--model-path", help="Optional override for the helmet model path.")
    parser.add_argument("--image", help="Optional local image path to run helmet detection on.")
    parser.add_argument("--video", help="Optional local video path to read one frame from.")
    return parser.parse_args()


def load_frame(image_path=None, video_path=None):
    """Load one image/video frame, or return a blank smoke-test frame."""
    if image_path and video_path:
        raise ValueError("Use either --image or --video, not both.")

    if image_path:
        import cv2

        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Unable to read image: {image_path}")
        return frame

    if video_path:
        import cv2

        capture = cv2.VideoCapture(video_path)
        ok, frame = capture.read()
        capture.release()
        if not ok or frame is None:
            raise ValueError(f"Unable to read first frame from video: {video_path}")
        return frame

    if not image_path and not video_path:
        return np.zeros((640, 640, 3), dtype=np.uint8)


def main():
    """Load helmet.pt, print model classes, and run one inference."""
    args = parse_args()
    detector = HelmetDetector(
        model_path=args.model_path or Config.HELMET_MODEL_PATH,
        provider=args.provider,
        confidence_threshold=Config.HELMET_WARNING_THRESHOLD,
        detection_confidence_threshold=Config.HELMET_CONFIDENCE_THRESHOLD,
        iou_threshold=Config.HELMET_IOU_THRESHOLD,
        device=Config.HELMET_DEVICE,
        image_size=Config.HELMET_IMAGE_SIZE,
        half_precision=Config.HELMET_HALF_PRECISION,
        cudnn_benchmark=Config.HELMET_CUDNN_BENCHMARK,
        match_upper_ratio=Config.HELMET_MATCH_UPPER_RATIO,
        class_ids=Config.HELMET_CLASS_IDS,
        helmet_class_id=Config.HELMET_CLASS_ID,
        no_helmet_class_id=Config.NO_HELMET_CLASS_ID,
    )
    frame = load_frame(args.image, args.video)
    detections = detector.detect(frame, frame_id="helmet-smoke-test")

    print(f"provider={detector.provider}")
    print(f"modelPath={Path(detector.model_path).resolve()}")
    print(f"device={detector.device}")
    print(f"classNames={detector.class_names}")
    print(f"detections={len(detections)}")
    for detection in detections[:10]:
        print(detection)


if __name__ == "__main__":
    main()
