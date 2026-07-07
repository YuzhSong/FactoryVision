import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_config import Config
from modules.person_detector import PersonDetector


def main():
    """Check torch CUDA status and run one blank YOLO person-detection inference."""
    print(f"torch={torch.__version__}")
    print(f"torch_cuda={torch.version.cuda}")
    print(f"cuda_available={torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"cuda_device={torch.cuda.get_device_name(0)}")

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
    detector.load_model()
    print(f"yolo_device={detector.device}")
    print(f"yolo_image_size={detector.image_size}")
    print(f"yolo_half_precision={detector.half_precision}")

    blank_frame = np.zeros((640, 640, 3), dtype=np.uint8)
    results = detector.detect(blank_frame, frame_id="cuda-check")
    print(f"person_results={len(results)}")


if __name__ == "__main__":
    main()
