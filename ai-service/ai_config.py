import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL_DIR = BASE_DIR / "models"
DEFAULT_DATA_DIR = BASE_DIR / "data"
DEFAULT_ULTRALYTICS_CONFIG_DIR = DEFAULT_DATA_DIR / "ultralytics"
DEFAULT_MATPLOTLIB_CONFIG_DIR = DEFAULT_DATA_DIR / "matplotlib"
DEFAULT_TORCH_HOME = DEFAULT_DATA_DIR / "torch"
DEFAULT_INSIGHTFACE_ROOT = DEFAULT_MODEL_DIR / "insightface"

os.environ.setdefault("YOLO_CONFIG_DIR", str(DEFAULT_ULTRALYTICS_CONFIG_DIR))
os.environ.setdefault("MPLCONFIGDIR", str(DEFAULT_MATPLOTLIB_CONFIG_DIR))
os.environ.setdefault("TORCH_HOME", str(DEFAULT_TORCH_HOME))
os.environ.setdefault("INSIGHTFACE_HOME", str(DEFAULT_INSIGHTFACE_ROOT))
os.environ.setdefault("NO_ALBUMENTATIONS_UPDATE", "1")


def _parse_size(value: str, default: tuple[int, int]):
    try:
        width, height = value.lower().replace("x", ",").split(",", maxsplit=1)
        return (int(width.strip()), int(height.strip()))
    except (AttributeError, TypeError, ValueError):
        return default


class Config:
    SERVICE_NAME = "smart-factory-ai-service"
    HOST = os.getenv("AI_SERVICE_HOST", "0.0.0.0")
    PORT = int(os.getenv("AI_SERVICE_PORT", "9000"))
    DEBUG = os.getenv("AI_SERVICE_DEBUG", "True").lower() == "true"
    BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000/api")
    BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")
    BACKEND_TIMEOUT_SECONDS = float(os.getenv("BACKEND_TIMEOUT_SECONDS", "5"))
    BACKEND_CAMERA_LIST_PATH = os.getenv("BACKEND_CAMERA_LIST_PATH", "/cameras/list/")
    BACKEND_EMPLOYEE_LIST_PATH = os.getenv("BACKEND_EMPLOYEE_LIST_PATH", "/employees/list/")
    BACKEND_FACE_LIBRARY_PATH = os.getenv("BACKEND_FACE_LIBRARY_PATH", "")
    BACKEND_ZONE_LIST_PATH = os.getenv("BACKEND_ZONE_LIST_PATH", "/zones/")
    BACKEND_AI_REPORT_PATH = os.getenv("BACKEND_AI_REPORT_PATH", "/ai-results/report/")

    MODEL_DIR = Path(os.getenv("AI_MODEL_DIR", DEFAULT_MODEL_DIR))
    DATA_DIR = Path(os.getenv("AI_DATA_DIR", DEFAULT_DATA_DIR))
    ULTRALYTICS_CONFIG_DIR = Path(
        os.getenv("YOLO_CONFIG_DIR", str(DEFAULT_ULTRALYTICS_CONFIG_DIR))
    )
    MATPLOTLIB_CONFIG_DIR = Path(
        os.getenv("MPLCONFIGDIR", str(DEFAULT_MATPLOTLIB_CONFIG_DIR))
    )
    TORCH_HOME = Path(os.getenv("TORCH_HOME", str(DEFAULT_TORCH_HOME)))
    INSIGHTFACE_ROOT = Path(os.getenv("INSIGHTFACE_HOME", str(DEFAULT_INSIGHTFACE_ROOT)))

    YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", str(MODEL_DIR / "yolo" / "yolov8n.pt"))
    YOLO_DEVICE = os.getenv("YOLO_DEVICE", "auto")
    YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "640"))
    YOLO_HALF_PRECISION = os.getenv("YOLO_HALF_PRECISION", "auto")
    YOLO_CUDNN_BENCHMARK = os.getenv("YOLO_CUDNN_BENCHMARK", "True").lower() == "true"
    PERSON_CONFIDENCE_THRESHOLD = float(os.getenv("PERSON_CONFIDENCE_THRESHOLD", "0.35"))
    PERSON_IOU_THRESHOLD = float(os.getenv("PERSON_IOU_THRESHOLD", "0.45"))
    PERSON_TRACK_IOU_THRESHOLD = float(os.getenv("PERSON_TRACK_IOU_THRESHOLD", "0.3"))
    PERSON_TRACK_MAX_MISSED_FRAMES = int(os.getenv("PERSON_TRACK_MAX_MISSED_FRAMES", "15"))

    FACE_MODEL_NAME = os.getenv("FACE_MODEL_NAME", "buffalo_l")
    FACE_DETECTION_SIZE = _parse_size(os.getenv("FACE_DETECTION_SIZE", "640,640"), (640, 640))
    FACE_LIBRARY_PATH = os.getenv("FACE_LIBRARY_PATH", str(DATA_DIR / "faces" / "face_library.json"))
    FACE_IMAGE_DIR = os.getenv("FACE_IMAGE_DIR", str(DATA_DIR / "faces" / "employees"))
    FACE_IMAGE_BASE_URL = os.getenv("FACE_IMAGE_BASE_URL", "")
    FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.45"))
    FACE_PROVIDER = os.getenv("FACE_PROVIDER", "auto")
    AUTO_LOAD_FACES_FROM_BACKEND = os.getenv("AUTO_LOAD_FACES_FROM_BACKEND", "True").lower() == "true"

    STREAM_RECONNECT_ATTEMPTS = int(os.getenv("STREAM_RECONNECT_ATTEMPTS", "3"))
    STREAM_RECONNECT_DELAY_SECONDS = float(os.getenv("STREAM_RECONNECT_DELAY_SECONDS", "1.0"))
    STREAM_MAX_FRAMES_PER_REQUEST = int(os.getenv("STREAM_MAX_FRAMES_PER_REQUEST", "30"))
    STREAM_SAMPLE_INTERVAL = int(os.getenv("STREAM_SAMPLE_INTERVAL", "1"))
    STREAM_INPUT_URL = os.getenv("STREAM_INPUT_URL", "rtmp://81.70.90.222:1935/live/1")
    STREAM_OUTPUT_URL = os.getenv("STREAM_OUTPUT_URL", "rtmp://81.70.90.222:1935/live/1_detected")
    STREAM_PLAY_URL = os.getenv("STREAM_PLAY_URL", "webrtc://webrtc.rainycode.cn:8443/live/1_detected")
    STREAM_PROCESS_MODE = os.getenv("STREAM_PROCESS_MODE", "detect")
    STREAM_REPORT_TO_BACKEND = os.getenv("STREAM_REPORT_TO_BACKEND", "False").lower() == "true"
    STREAM_OUTPUT_FPS = float(os.getenv("STREAM_OUTPUT_FPS", "25"))
    STREAM_FFMPEG_PATH = os.getenv("STREAM_FFMPEG_PATH", "ffmpeg")
