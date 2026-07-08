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
    parser.add_argument("--image", help="Optional local image path to run helmet detection on.")
    return parser.parse_args()


def load_frame(image_path):
    """Load an image with OpenCV or return a blank smoke-test frame."""
    if not image_path:
        return np.zeros((640, 640, 3), dtype=np.uint8)

    import cv2

    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Unable to read image: {image_path}")
    return frame


def main():
    """Load helmet.pt, print model classes, and run one inference."""
    args = parse_args()
    detector = HelmetDetector(
        model_path=Config.HELMET_MODEL_PATH,
        confidence_threshold=Config.HELMET_WARNING_THRESHOLD,
        detection_confidence_threshold=Config.HELMET_CONFIDENCE_THRESHOLD,
        iou_threshold=Config.HELMET_IOU_THRESHOLD,
        device=Config.HELMET_DEVICE,
        image_size=Config.HELMET_IMAGE_SIZE,
        half_precision=Config.HELMET_HALF_PRECISION,
        cudnn_benchmark=Config.HELMET_CUDNN_BENCHMARK,
    )
    frame = load_frame(args.image)
    detections = detector.detect(frame, frame_id="helmet-smoke-test")

    print(f"modelPath={Path(Config.HELMET_MODEL_PATH).resolve()}")
    print(f"device={detector.device}")
    print(f"classNames={detector.class_names}")
    print(f"detections={len(detections)}")
    for detection in detections[:10]:
        print(detection)


if __name__ == "__main__":
    main()
