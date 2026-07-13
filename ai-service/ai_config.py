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


def _parse_csv(value: str, default: list[str]):
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or default


class Config:
    SERVICE_NAME = "smart-factory-ai-service"
    HOST = os.getenv("AI_SERVICE_HOST", "0.0.0.0")
    PORT = int(os.getenv("AI_SERVICE_PORT", "9000"))
    CORS_ORIGINS = _parse_csv(
        os.getenv(
            "AI_SERVICE_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,https://webrtc.rainycode.cn,https://webrtc.rainycode.cn:8443",
        ),
        [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "https://webrtc.rainycode.cn",
            "https://webrtc.rainycode.cn:8443",
        ],
    )
    # Reloading starts a parent/child process pair and makes local stop/restart unreliable.
    DEBUG = os.getenv("AI_SERVICE_DEBUG", "False").lower() == "true"
    BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000/api")
    BACKEND_API_TOKEN = os.getenv("BACKEND_API_TOKEN", "")
    BACKEND_TIMEOUT_SECONDS = float(os.getenv("BACKEND_TIMEOUT_SECONDS", "5"))
    BACKEND_TLS_VERIFY = os.getenv("BACKEND_TLS_VERIFY", "True").lower() not in {"0", "false", "no", "off"}
    BACKEND_CAMERA_LIST_PATH = os.getenv("BACKEND_CAMERA_LIST_PATH", "/cameras/list/")
    BACKEND_EMPLOYEE_LIST_PATH = os.getenv("BACKEND_EMPLOYEE_LIST_PATH", "/employees/list/")
    # Face vectors are fetched through a dedicated AI-to-backend endpoint, never a browser JWT.
    BACKEND_FACE_LIBRARY_PATH = os.getenv("BACKEND_FACE_LIBRARY_PATH", "/face/library/")
    BACKEND_ZONE_LIST_PATH = os.getenv("BACKEND_ZONE_LIST_PATH", "/zones/list/")
    BACKEND_AI_REPORT_PATH = os.getenv("BACKEND_AI_REPORT_PATH", "/ai-results/report/")
    BACKEND_BOOTSTRAP_PATH = os.getenv("BACKEND_BOOTSTRAP_PATH", "/ai/bootstrap/")
    BOOTSTRAP_ON_STARTUP = os.getenv("BOOTSTRAP_ON_STARTUP", "False").lower() == "true"

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
    HELMET_MODEL_PATH = os.getenv("HELMET_MODEL_PATH", str(MODEL_DIR / "helmet" / "helmet.pt"))
    HELMET_MODEL_PROVIDER = os.getenv("HELMET_MODEL_PROVIDER", "opensource").strip().lower()
    HELMET_DEVICE = os.getenv("HELMET_DEVICE", YOLO_DEVICE)
    HELMET_IMAGE_SIZE = int(os.getenv("HELMET_IMAGE_SIZE", str(YOLO_IMAGE_SIZE)))
    HELMET_HALF_PRECISION = os.getenv("HELMET_HALF_PRECISION", YOLO_HALF_PRECISION)
    HELMET_CUDNN_BENCHMARK = os.getenv("HELMET_CUDNN_BENCHMARK", str(YOLO_CUDNN_BENCHMARK)).lower() == "true"
    HELMET_CONFIDENCE_THRESHOLD = float(os.getenv("HELMET_CONFIDENCE_THRESHOLD", "0.35"))
    HELMET_IOU_THRESHOLD = float(os.getenv("HELMET_IOU_THRESHOLD", "0.45"))
    HELMET_WARNING_THRESHOLD = float(os.getenv("HELMET_WARNING_THRESHOLD", str(HELMET_CONFIDENCE_THRESHOLD)))
    HELMET_MATCH_UPPER_RATIO = float(os.getenv("HELMET_MATCH_UPPER_RATIO", "0.65"))
    HELMET_MAX_DET = int(os.getenv("HELMET_MAX_DET", "300"))
    HELMET_CLASS_IDS = tuple(
        int(value.strip())
        for value in os.getenv("HELMET_CLASS_IDS", "3,8").split(",")
        if value.strip()
    )
    HELMET_CLASS_ID = int(os.getenv("HELMET_CLASS_ID", "3"))
    NO_HELMET_CLASS_ID = int(os.getenv("NO_HELMET_CLASS_ID", "8"))

    FACE_MODEL_NAME = os.getenv("FACE_MODEL_NAME", "buffalo_l")
    FACE_DETECTION_SIZE = _parse_size(os.getenv("FACE_DETECTION_SIZE", "640,640"), (640, 640))
    FACE_LIBRARY_PATH = os.getenv("FACE_LIBRARY_PATH", str(DATA_DIR / "faces" / "face_library.json"))
    FACE_IMAGE_DIR = os.getenv("FACE_IMAGE_DIR", str(DATA_DIR / "faces" / "employees"))
    FACE_IMAGE_BASE_URL = os.getenv("FACE_IMAGE_BASE_URL", "")
    FACE_SIMILARITY_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.45"))
    FACE_MIN_SCORE_MARGIN = float(os.getenv("FACE_MIN_SCORE_MARGIN", "0.03"))
    FACE_MIN_SAMPLES_PER_EMPLOYEE = int(os.getenv("FACE_MIN_SAMPLES_PER_EMPLOYEE", "2"))
    FACE_SPARSE_SAMPLE_THRESHOLD_PENALTY = float(os.getenv("FACE_SPARSE_SAMPLE_THRESHOLD_PENALTY", "0.03"))
    FACE_ENROLLMENT_MIN_QUALITY_SCORE = float(os.getenv("FACE_ENROLLMENT_MIN_QUALITY_SCORE", "0.5"))
    FACE_ENROLLMENT_MIN_FACE_SIZE = int(os.getenv("FACE_ENROLLMENT_MIN_FACE_SIZE", "40"))
    FACE_ENROLLMENT_MAX_POSE_YAW = float(os.getenv("FACE_ENROLLMENT_MAX_POSE_YAW", "75"))
    LIVENESS_ENABLED = os.getenv("LIVENESS_ENABLED", "False").lower() == "true"
    LIVENESS_REQUIRED = os.getenv("LIVENESS_REQUIRED", "False").lower() == "true"
    LIVENESS_PROVIDER = os.getenv("LIVENESS_PROVIDER", "rgb_quality_heuristic")
    LIVENESS_THRESHOLD = float(os.getenv("LIVENESS_THRESHOLD", "0.70"))
    LIVENESS_MODEL_PATH = os.getenv("LIVENESS_MODEL_PATH", "")
    LIVENESS_MIN_FACE_SIZE = int(os.getenv("LIVENESS_MIN_FACE_SIZE", "48"))
    FACE_PROVIDER = os.getenv("FACE_PROVIDER", "auto")
    AUTO_LOAD_FACES_FROM_BACKEND = os.getenv("AUTO_LOAD_FACES_FROM_BACKEND", "True").lower() == "true"
    MODEL_WARMUP_ON_STARTUP = os.getenv("MODEL_WARMUP_ON_STARTUP", "False").lower() == "true"
    MODEL_WARMUP_INCLUDE_FACE = os.getenv("MODEL_WARMUP_INCLUDE_FACE", "True").lower() == "true"

    STREAM_RECONNECT_ATTEMPTS = int(os.getenv("STREAM_RECONNECT_ATTEMPTS", "3"))
    STREAM_RECONNECT_DELAY_SECONDS = float(os.getenv("STREAM_RECONNECT_DELAY_SECONDS", "1.0"))
    STREAM_MAX_FRAMES_PER_REQUEST = int(os.getenv("STREAM_MAX_FRAMES_PER_REQUEST", "30"))
    STREAM_SAMPLE_INTERVAL = int(os.getenv("STREAM_SAMPLE_INTERVAL", "1"))
    STREAM_INPUT_URL = os.getenv("STREAM_INPUT_URL", "rtmp://81.70.90.222:1935/live/1")
    STREAM_OUTPUT_URL = os.getenv("STREAM_OUTPUT_URL", "rtmp://81.70.90.222:1935/live/1_detected")
    STREAM_PLAY_URL = os.getenv("STREAM_PLAY_URL", "webrtc://webrtc.rainycode.cn:8443/live/1_detected")
    STREAM_PROCESS_MODE = os.getenv("STREAM_PROCESS_MODE", "detect")
    STREAM_REPORT_TO_BACKEND = os.getenv("STREAM_REPORT_TO_BACKEND", "False").lower() == "true"
    STREAM_REPORT_REALTIME_TO_BACKEND = os.getenv("STREAM_REPORT_REALTIME_TO_BACKEND", "False").lower() == "true"
    EVENT_REPORT_QUEUE_SIZE = int(os.getenv("EVENT_REPORT_QUEUE_SIZE", "128"))
    STREAM_OUTPUT_FPS = float(os.getenv("OUTPUT_FPS", os.getenv("STREAM_OUTPUT_FPS", "10")))
    STREAM_FFMPEG_PATH = os.getenv("STREAM_FFMPEG_PATH", "ffmpeg")
    FRAME_DETECT_INTERVAL = int(os.getenv("FRAME_DETECT_INTERVAL", "5"))
    # Run one expensive model per analysis tick by default. The intervals are based on
    # processed output frames, so they remain stable when capture drops source frames.
    PERSON_DETECT_INTERVAL = int(os.getenv("PERSON_DETECT_INTERVAL", "5"))
    HELMET_DETECT_INTERVAL = int(os.getenv("HELMET_DETECT_INTERVAL", "8"))
    HELMET_DETECT_OFFSET = int(os.getenv("HELMET_DETECT_OFFSET", "4"))
    STREAM_INCLUDE_FACES_DEFAULT = os.getenv("STREAM_INCLUDE_FACES_DEFAULT", "False").lower() == "true"
    FACE_DETECT_INTERVAL = int(os.getenv("FACE_RECOGNITION_INTERVAL", os.getenv("FACE_DETECT_INTERVAL", "30")))
    FACE_DETECT_OFFSET = int(os.getenv("FACE_DETECT_OFFSET", "2"))
    DETECTION_CACHE_MAX_AGE_FRAMES = int(os.getenv("DETECTION_CACHE_MAX_AGE_FRAMES", "20"))
    ANNOTATION_LINE_WIDTH = int(os.getenv("ANNOTATION_LINE_WIDTH", "1"))
    ANNOTATION_LABEL_SCALE = float(os.getenv("ANNOTATION_LABEL_SCALE", "0.28"))
    EVENT_MEDIA_ENABLED = os.getenv("EVENT_MEDIA_ENABLED", "True").lower() == "true"
    EVENT_MEDIA_DIR = os.getenv("EVENT_MEDIA_DIR", str(DATA_DIR / "event_media"))
    EVENT_MEDIA_PRE_SECONDS = float(os.getenv("EVENT_MEDIA_PRE_SECONDS", "3"))
    EVENT_MEDIA_POST_SECONDS = float(os.getenv("EVENT_MEDIA_POST_SECONDS", "3"))
    EVENT_MEDIA_COOLDOWN_SECONDS = float(os.getenv("EVENT_MEDIA_COOLDOWN_SECONDS", "10"))
    # Keep real detector observations before and after a posture transition. Cached
    # display frames are deliberately excluded from this history.
    MAX_HISTORY_POINTS = int(os.getenv("MAX_HISTORY_POINTS", "12"))
    INPUT_WIDTH = int(os.getenv("INPUT_WIDTH", "640"))
    INPUT_HEIGHT = int(os.getenv("INPUT_HEIGHT", "360"))
    RUNNING_SPEED_THRESHOLD = float(os.getenv("RUNNING_SPEED_THRESHOLD", "120.0"))
    # Keep a confirmed identity across the default 30-frame face interval at ~5 FPS.
    FACE_IDENTITY_CACHE_SECONDS = float(os.getenv("FACE_IDENTITY_CACHE_SECONDS", "10"))
    FACE_UNKNOWN_CACHE_SECONDS = float(os.getenv("FACE_UNKNOWN_CACHE_SECONDS", "1"))
    FACE_TRACK_TTL_SECONDS = float(os.getenv("FACE_TRACK_TTL_SECONDS", "30"))
    FACE_RECOGNIZED_COOLDOWN_SECONDS = float(os.getenv("FACE_RECOGNIZED_COOLDOWN_SECONDS", "60"))
    ZONE_MIN_STAY_SECONDS = float(os.getenv("ZONE_MIN_STAY_SECONDS", "5"))
    ZONE_STATE_TTL_SECONDS = float(os.getenv("ZONE_STATE_TTL_SECONDS", "30"))
    ZONE_ENTER_CONFIRM_SECONDS = float(os.getenv("ZONE_ENTER_CONFIRM_SECONDS", "0.3"))
    ZONE_EXIT_CONFIRM_SECONDS = float(os.getenv("ZONE_EXIT_CONFIRM_SECONDS", "1.0"))
    ZONE_REFRESH_INTERVAL_SECONDS = float(os.getenv("ZONE_REFRESH_INTERVAL_SECONDS", "10"))
    HELMET_EVENT_COOLDOWN_SECONDS = float(os.getenv("HELMET_EVENT_COOLDOWN_SECONDS", "60"))
    HELMET_RESULT_CACHE_TTL_SECONDS = float(os.getenv("HELMET_RESULT_CACHE_TTL_SECONDS", str(FACE_IDENTITY_CACHE_SECONDS)))
    TRACK_STATE_TTL_SECONDS = float(os.getenv("TRACK_STATE_TTL_SECONDS", "30"))
    FALL_RATIO_THRESHOLD = float(os.getenv("FALL_RATIO_THRESHOLD", "1.2"))
    FALL_CONFIRM_FRAMES = int(os.getenv("FALL_CONFIRM_FRAMES", "5"))
    FALL_MIN_CONFIDENCE = float(os.getenv("FALL_MIN_CONFIDENCE", "0.6"))
    FALL_POSE_HORIZONTAL_ANGLE_THRESHOLD = float(os.getenv("FALL_POSE_HORIZONTAL_ANGLE_THRESHOLD", "35"))
    FALL_POSE_MIN_KEYPOINT_CONFIDENCE = float(os.getenv("FALL_POSE_MIN_KEYPOINT_CONFIDENCE", "0.3"))
    FALL_BBOX_EDGE_MARGIN_RATIO = float(os.getenv("FALL_BBOX_EDGE_MARGIN_RATIO", "0.02"))
    FALL_MIN_CENTER_DROP_RATIO = float(os.getenv("FALL_MIN_CENTER_DROP_RATIO", "0.15"))
    FALL_MIN_HEIGHT_DROP_RATIO = float(os.getenv("FALL_MIN_HEIGHT_DROP_RATIO", "0.2"))
    FALL_MAX_TRANSITION_SECONDS = float(os.getenv("FALL_MAX_TRANSITION_SECONDS", "2.0"))
    FALL_SUSTAINED_LOW_DROP_RATIO = float(os.getenv("FALL_SUSTAINED_LOW_DROP_RATIO", "0.4"))
    FALL_LOW_POSTURE_HEIGHT_RATIO = float(os.getenv("FALL_LOW_POSTURE_HEIGHT_RATIO", "0.7"))
    FALL_VERY_LOW_HEIGHT_RATIO = float(os.getenv("FALL_VERY_LOW_HEIGHT_RATIO", "0.58"))
    FALL_SLOW_TRANSITION_SECONDS = float(os.getenv("FALL_SLOW_TRANSITION_SECONDS", "6.0"))
    FALL_RECOVER_FRAMES = int(os.getenv("FALL_RECOVER_FRAMES", "2"))
    FALL_STATE_TTL_SECONDS = float(os.getenv("FALL_STATE_TTL_SECONDS", str(TRACK_STATE_TTL_SECONDS)))
    EMPLOYEE_ABSENCE_TIMEOUT_SECONDS = float(os.getenv("EMPLOYEE_ABSENCE_TIMEOUT_SECONDS", "60"))
    EMPLOYEE_PRESENCE_MIN_SIMILARITY = float(os.getenv("EMPLOYEE_PRESENCE_MIN_SIMILARITY", "0"))
    STRANGER_CONFIRM_FRAMES = int(os.getenv("STRANGER_CONFIRM_FRAMES", "3"))
    STRANGER_COOLDOWN_SECONDS = float(os.getenv("STRANGER_COOLDOWN_SECONDS", "30"))
    STRANGER_MATCH_DISTANCE_THRESHOLD = float(os.getenv("STRANGER_MATCH_DISTANCE_THRESHOLD", "80"))
    STRANGER_STATE_TTL_SECONDS = float(os.getenv("STRANGER_STATE_TTL_SECONDS", "10"))
