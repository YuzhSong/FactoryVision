from datetime import datetime, timezone
import logging
import threading
import time
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from ai_config import Config
from modules.backend_client import BackendClient
from modules.dependencies import check_dependencies
from modules.face_recognition_service import FaceRecognitionService
from modules.frame_processor import FrameProcessor
from modules.frame_annotator import FrameAnnotator
from modules.person_detector import PersonDetector
from modules.processed_stream_service import ProcessedStreamService, normalize_camera_frame
from modules.runtime_cache import RuntimeCache
from modules.stream_reader import StreamReader


logger = logging.getLogger("uvicorn.error")

backend_client = BackendClient(
    base_url=Config.BACKEND_API_BASE_URL,
    timeout_seconds=Config.BACKEND_TIMEOUT_SECONDS,
    token=Config.BACKEND_API_TOKEN,
    tls_verify=Config.BACKEND_TLS_VERIFY,
    camera_list_path=Config.BACKEND_CAMERA_LIST_PATH,
    employee_list_path=Config.BACKEND_EMPLOYEE_LIST_PATH,
    face_library_path=Config.BACKEND_FACE_LIBRARY_PATH,
    zone_list_path=Config.BACKEND_ZONE_LIST_PATH,
    ai_report_path=Config.BACKEND_AI_REPORT_PATH,
    bootstrap_path=Config.BACKEND_BOOTSTRAP_PATH,
)

person_detector = PersonDetector(
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

face_service = FaceRecognitionService(
    model_name=Config.FACE_MODEL_NAME,
    model_root=Config.INSIGHTFACE_ROOT,
    similarity_threshold=Config.FACE_SIMILARITY_THRESHOLD,
    min_score_margin=Config.FACE_MIN_SCORE_MARGIN,
    min_samples_per_employee=Config.FACE_MIN_SAMPLES_PER_EMPLOYEE,
    sparse_sample_threshold_penalty=Config.FACE_SPARSE_SAMPLE_THRESHOLD_PENALTY,
    enrollment_min_quality_score=Config.FACE_ENROLLMENT_MIN_QUALITY_SCORE,
    enrollment_min_face_size=Config.FACE_ENROLLMENT_MIN_FACE_SIZE,
    enrollment_max_pose_yaw=Config.FACE_ENROLLMENT_MAX_POSE_YAW,
    liveness_enabled=Config.LIVENESS_ENABLED,
    liveness_required=Config.LIVENESS_REQUIRED,
    liveness_provider=Config.LIVENESS_PROVIDER,
    liveness_threshold=Config.LIVENESS_THRESHOLD,
    liveness_model_path=Config.LIVENESS_MODEL_PATH,
    liveness_min_face_size=Config.LIVENESS_MIN_FACE_SIZE,
    det_size=Config.FACE_DETECTION_SIZE,
    provider=Config.FACE_PROVIDER,
    library_path=Config.FACE_LIBRARY_PATH,
    image_dir=Config.FACE_IMAGE_DIR,
    image_base_url=Config.FACE_IMAGE_BASE_URL,
)

frame_processor = FrameProcessor(
    person_detector=person_detector,
    face_service=face_service,
    history_limit=Config.MAX_HISTORY_POINTS,
    abnormal_config={
        "runningSpeedThreshold": Config.RUNNING_SPEED_THRESHOLD,
        "helmetModelPath": Config.HELMET_MODEL_PATH,
        "helmetModelProvider": Config.HELMET_MODEL_PROVIDER,
        "helmetDetectionConfidenceThreshold": Config.HELMET_CONFIDENCE_THRESHOLD,
        "helmetIouThreshold": Config.HELMET_IOU_THRESHOLD,
        "helmetConfidenceThreshold": Config.HELMET_WARNING_THRESHOLD,
        "helmetDevice": Config.HELMET_DEVICE,
        "helmetImageSize": Config.HELMET_IMAGE_SIZE,
        "helmetHalfPrecision": Config.HELMET_HALF_PRECISION,
        "helmetCudnnBenchmark": Config.HELMET_CUDNN_BENCHMARK,
        "helmetMatchUpperRatio": Config.HELMET_MATCH_UPPER_RATIO,
        "helmetMaxDet": Config.HELMET_MAX_DET,
        "helmetClassIds": Config.HELMET_CLASS_IDS,
        "helmetClassId": Config.HELMET_CLASS_ID,
        "noHelmetClassId": Config.NO_HELMET_CLASS_ID,
        "zoneMinStaySeconds": Config.ZONE_MIN_STAY_SECONDS,
        "zoneStateTtlSeconds": Config.ZONE_STATE_TTL_SECONDS,
        "zoneEnterConfirmSeconds": Config.ZONE_ENTER_CONFIRM_SECONDS,
        "zoneExitConfirmSeconds": Config.ZONE_EXIT_CONFIRM_SECONDS,
        "helmetEventCooldownSeconds": Config.HELMET_EVENT_COOLDOWN_SECONDS,
        "trackStateTtlSeconds": Config.TRACK_STATE_TTL_SECONDS,
        "faceIdentityCacheSeconds": Config.FACE_IDENTITY_CACHE_SECONDS,
        "faceUnknownCacheSeconds": Config.FACE_UNKNOWN_CACHE_SECONDS,
        "faceTrackTtlSeconds": Config.FACE_TRACK_TTL_SECONDS,
        "faceRecognizedCooldownSeconds": Config.FACE_RECOGNIZED_COOLDOWN_SECONDS,
        "fallRatioThreshold": Config.FALL_RATIO_THRESHOLD,
        "fallConfirmFrames": Config.FALL_CONFIRM_FRAMES,
        "fallMinConfidence": Config.FALL_MIN_CONFIDENCE,
        "fallPoseHorizontalAngleThreshold": Config.FALL_POSE_HORIZONTAL_ANGLE_THRESHOLD,
        "fallPoseMinKeypointConfidence": Config.FALL_POSE_MIN_KEYPOINT_CONFIDENCE,
        "fallBboxEdgeMarginRatio": Config.FALL_BBOX_EDGE_MARGIN_RATIO,
        "fallMinCenterDropRatio": Config.FALL_MIN_CENTER_DROP_RATIO,
        "fallMinHeightDropRatio": Config.FALL_MIN_HEIGHT_DROP_RATIO,
        "fallMaxTransitionSeconds": Config.FALL_MAX_TRANSITION_SECONDS,
        "fallRecoverFrames": Config.FALL_RECOVER_FRAMES,
        "fallStateTtlSeconds": Config.FALL_STATE_TTL_SECONDS,
        "employeeAbsenceTimeoutSeconds": Config.EMPLOYEE_ABSENCE_TIMEOUT_SECONDS,
        "employeePresenceMinSimilarity": Config.EMPLOYEE_PRESENCE_MIN_SIMILARITY,
        "strangerConfirmFrames": Config.STRANGER_CONFIRM_FRAMES,
        "strangerCooldownSeconds": Config.STRANGER_COOLDOWN_SECONDS,
        "strangerMatchDistanceThreshold": Config.STRANGER_MATCH_DISTANCE_THRESHOLD,
        "strangerStateTtlSeconds": Config.STRANGER_STATE_TTL_SECONDS,
    },
)

processed_stream_service = ProcessedStreamService(
    frame_processor=frame_processor,
    backend_client=backend_client,
    default_input_url=Config.STREAM_INPUT_URL,
    default_output_url=Config.STREAM_OUTPUT_URL,
    default_play_url=Config.STREAM_PLAY_URL,
    default_mode=Config.STREAM_PROCESS_MODE,
    default_report_to_backend=Config.STREAM_REPORT_TO_BACKEND,
    reconnect_attempts=Config.STREAM_RECONNECT_ATTEMPTS,
    reconnect_delay_seconds=Config.STREAM_RECONNECT_DELAY_SECONDS,
    output_fps=Config.STREAM_OUTPUT_FPS,
    ffmpeg_path=Config.STREAM_FFMPEG_PATH,
    detect_interval=Config.FRAME_DETECT_INTERVAL,
    person_detect_interval=Config.PERSON_DETECT_INTERVAL,
    helmet_detect_interval=Config.HELMET_DETECT_INTERVAL,
    helmet_detect_offset=Config.HELMET_DETECT_OFFSET,
    face_detect_interval=Config.FACE_DETECT_INTERVAL,
    face_detect_offset=Config.FACE_DETECT_OFFSET,
    detection_cache_max_age_frames=Config.DETECTION_CACHE_MAX_AGE_FRAMES,
    annotator=FrameAnnotator(
        line_width=Config.ANNOTATION_LINE_WIDTH,
        label_scale=Config.ANNOTATION_LABEL_SCALE,
    ),
    input_width=Config.INPUT_WIDTH,
    input_height=Config.INPUT_HEIGHT,
    event_media_enabled=Config.EVENT_MEDIA_ENABLED,
    event_media_dir=Config.EVENT_MEDIA_DIR,
    event_media_pre_seconds=Config.EVENT_MEDIA_PRE_SECONDS,
    event_media_post_seconds=Config.EVENT_MEDIA_POST_SECONDS,
    event_media_cooldown_seconds=Config.EVENT_MEDIA_COOLDOWN_SECONDS,
)

runtime_cache = RuntimeCache()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Factory AI Service",
        description="Video-frame analysis, person detection, face recognition, and behavior reporting service.",
        version="0.2.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def bootstrap_runtime_cache_on_startup():
        if Config.BOOTSTRAP_ON_STARTUP:
            try:
                _bootstrap_from_backend()
            except Exception as exc:
                runtime_cache.set_error(exc)
        if Config.MODEL_WARMUP_ON_STARTUP:
            _start_model_warmup()

    @app.get("/health", tags=["system"])
    def health_check():
        return {
            "service": Config.SERVICE_NAME,
            "status": "ok",
            "stage": "cuda-yolo-frame-pipeline-ready",
            "docs": "/docs",
            "faceLibrary": face_service.status(),
            "runtimeCache": runtime_cache.status(),
        }

    @app.get("/dependencies", tags=["system"])
    def dependencies_check():
        return {
            "service": Config.SERVICE_NAME,
            "dependencies": check_dependencies(),
        }

    @app.post("/streams/start", tags=["stream"])
    async def start_processed_stream(request: Request):
        try:
            payload = await _payload(request)
            if _to_bool(payload.get("reportRealtimeToBackend")):
                raise ValueError("`reportRealtimeToBackend` is no longer supported; use `reportToBackend`.")
            camera_id = payload.get("cameraId")
            if camera_id and not isinstance(payload.get("zones"), list):
                payload["zones"] = _resolve_zones({**payload, "loadZonesFromBackend": True}, camera_id) or []
            if _to_bool(payload.get("includeFaces", Config.STREAM_INCLUDE_FACES_DEFAULT)):
                try:
                    _maybe_load_faces_for_stream(payload, True)
                except Exception as exc:
                    logger.warning("Face library load failed before stream start; continuing without faces: %s", exc)
            status = processed_stream_service.start(payload)
        except Exception as exc:
            return _error_response(exc)

        return {"code": 200, "message": "success", "data": status}

    @app.post("/streams/stop", tags=["stream"])
    def stop_processed_stream():
        return {"code": 200, "message": "success", "data": processed_stream_service.stop()}

    @app.get("/streams/status", tags=["stream"])
    def processed_stream_status():
        return {"code": 200, "message": "success", "data": processed_stream_service.status()}

    @app.get("/faces/status", tags=["faces"])
    def face_status():
        return {"code": 200, "message": "success", "data": face_service.status()}

    @app.post("/faces/extract", tags=["faces"], response_model=FaceExtractResponse)
    async def extract_face_feature(
        request: Request,
        image: UploadFile | None = File(default=None),
        image_path_form: str | None = Form(default=None, alias="imagePath"),
        image_url_form: str | None = Form(default=None, alias="imageUrl"),
        image_base64_form: str | None = Form(default=None, alias="imageBase64"),
        image_base_url_form: str | None = Form(default=None, alias="imageBaseUrl"),
        image_dir_form: str | None = Form(default=None, alias="imageDir"),
        require_single_face_form: Any = Form(default=None, alias="requireSingleFace"),
    ):
        try:
            payload = await _payload(request)
            frame_or_source = await _resolve_face_image_source(
                image=image,
                payload=payload,
                image_path_form=image_path_form,
                image_url_form=image_url_form,
                image_base64_form=image_base64_form,
            )
            require_single_face = _to_bool(
                _first_present(payload.get("requireSingleFace"), require_single_face_form, True)
            )
            result = face_service.extract_feature_details(
                frame_or_source,
                image_base_url=_first_present(
                    payload.get("imageBaseUrl"),
                    image_base_url_form,
                    Config.FACE_IMAGE_BASE_URL,
                ),
                image_dir=_first_present(payload.get("imageDir"), image_dir_form),
                require_single_face=require_single_face,
            )
            for key in ("employeeId", "employeeNo", "name"):
                if key in payload:
                    result[key] = payload[key]
        except Exception as exc:
            return _error_response(exc)

        return {"code": 200, "message": "success", "data": result}

    @app.post("/faces/reload", tags=["faces"])
    async def reload_faces(request: Request):
        try:
            payload = await _payload(request)
            result = _reload_face_library(payload)
        except Exception as exc:
            return _error_response(exc)

        return {"code": 200, "message": "success", "data": result}

    @app.get("/cache/status", tags=["cache"])
    def cache_status():
        return {
            "code": 200,
            "message": "success",
            "data": {
                "runtimeCache": runtime_cache.status(),
                "faceLibrary": face_service.status(),
            },
        }

    @app.post("/cache/reload", tags=["cache"])
    async def reload_runtime_cache(request: Request):
        try:
            payload = await _payload(request)
            result = _reload_runtime_cache(payload)
        except Exception as exc:
            return _error_response(exc)
        return {"code": 200, "message": "success", "data": result}

    @app.post("/cache/employees/upsert", tags=["cache"])
    async def upsert_employee_cache(request: Request):
        try:
            payload = await _payload(request)
            result = face_service.upsert_face_library(
                records=_as_list(payload.get("records") or payload.get("record")),
                employee_items=_as_list(payload.get("employees") or payload.get("employee")),
                image_base_url=payload.get("imageBaseUrl", Config.FACE_IMAGE_BASE_URL),
                image_dir=payload.get("imageDir"),
            )
        except Exception as exc:
            return _error_response(exc)
        return {"code": 200, "message": "success", "data": result}

    @app.post("/cache/employees/delete", tags=["cache"])
    async def delete_employee_cache(request: Request):
        try:
            payload = await _payload(request)
            result = face_service.delete_face_records(
                employee_ids=_as_list(
                    payload.get("employeeIds") or payload.get("employee_ids") or payload.get("employeeId")
                ),
                employee_nos=_as_list(
                    payload.get("employeeNos") or payload.get("employee_nos") or payload.get("employeeNo")
                ),
            )
        except Exception as exc:
            return _error_response(exc)
        return {"code": 200, "message": "success", "data": result}

    @app.post("/cache/cameras/reload", tags=["cache"])
    async def reload_camera_cache(request: Request):
        try:
            payload = await _payload(request)
            result = _reload_camera_cache(payload)
        except Exception as exc:
            return _error_response(exc)
        return {"code": 200, "message": "success", "data": result}

    @app.post("/cache/zones/reload", tags=["cache"])
    async def reload_zone_cache(request: Request):
        try:
            payload = await _payload(request)
            result = _reload_zone_cache(payload)
        except Exception as exc:
            return _error_response(exc)
        return {"code": 200, "message": "success", "data": result}

    @app.post("/detect/person", tags=["detection"])
    async def detect_person(
        request: Request,
        image: UploadFile | None = File(default=None),
        camera_id_form: Any = Form(default=None, alias="cameraId"),
        frame_id_form: Any = Form(default=None, alias="frameId"),
        image_path_form: str | None = Form(default=None, alias="imagePath"),
    ):
        try:
            payload = await _payload(request)
            frame = await _read_frame(image=image, image_path=image_path_form or payload.get("imagePath"))
            frame_id = frame_id_form or payload.get("frameId")
            camera_id = camera_id_form or payload.get("cameraId")
            results = person_detector.detect(frame, frame_id=frame_id)
        except Exception as exc:
            return _error_response(exc)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "cameraId": _to_number(camera_id),
                "frameId": frame_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": results,
            },
        }

    @app.post("/detect/frame", tags=["detection"])
    async def detect_frame(
        request: Request,
        image: UploadFile | None = File(default=None),
        camera_id_form: Any = Form(default=None, alias="cameraId"),
        frame_id_form: Any = Form(default=None, alias="frameId"),
        image_path_form: str | None = Form(default=None, alias="imagePath"),
        include_faces_form: Any = Form(default=None, alias="includeFaces"),
        reload_faces_form: Any = Form(default=None, alias="reloadFaces"),
    ):
        try:
            payload = await _payload(request)
            frame = await _read_frame(image=image, image_path=image_path_form or payload.get("imagePath"))
            if _to_bool(_first_present(payload.get("reloadFaces"), reload_faces_form)):
                _reload_face_library(payload)

            camera_id = camera_id_form or payload.get("cameraId")
            frame_id = frame_id_form or payload.get("frameId")
            include_faces = _to_bool(_first_present(payload.get("includeFaces"), include_faces_form, True))
            zones = _resolve_zones(payload, camera_id)
            report = frame_processor.process_frame(
                frame,
                camera_id=_to_number(camera_id),
                frame_id=frame_id,
                include_faces=include_faces,
                zones=zones,
            )
        except Exception as exc:
            return _error_response(exc)

        return {"code": 200, "message": "success", "data": report}

    @app.post("/process/stream", tags=["stream"])
    async def process_stream(request: Request):
        reader = None
        try:
            payload = await _payload(request)
            if _to_bool(payload.get("reportRealtimeToBackend", False)):
                raise ValueError("`reportRealtimeToBackend` is no longer supported; use `reportToBackend`.")
            stream_url, camera_id = _resolve_stream_source(payload)
            max_frames = _bounded_frame_count(payload.get("maxFrames", 1))
            sample_interval = int(payload.get("sampleInterval", Config.STREAM_SAMPLE_INTERVAL) or 1)
            include_faces = _to_bool(payload.get("includeFaces", True))
            face_library_result = _maybe_load_faces_for_stream(payload, include_faces)
            report_to_backend = _to_bool(payload.get("reportToBackend", False))
            zones = _resolve_zones(payload, camera_id)

            reader = StreamReader(
                reconnect_attempts=Config.STREAM_RECONNECT_ATTEMPTS,
                reconnect_delay_seconds=Config.STREAM_RECONNECT_DELAY_SECONDS,
            ).open_stream(stream_url)

            reports = []
            report_responses = []
            for packet in reader.iter_frames(max_frames=max_frames, sample_interval=sample_interval):
                packet.frame = normalize_camera_frame(packet.frame)
                report = frame_processor.process_frame(
                    packet.frame,
                    camera_id=_to_number(camera_id),
                    frame_id=packet.frame_id,
                    timestamp=packet.timestamp,
                    include_faces=include_faces,
                    frame_index=packet.frame_index,
                    fps=packet.fps,
                    zones=zones,
                )
                reports.append(report)
                if report_to_backend:
                    reportable = processed_stream_service._reportable_event_report(report)
                    if reportable["results"]:
                        report_responses.append(backend_client.report_ai_results(reportable))
        except Exception as exc:
            return _error_response(exc)
        finally:
            if reader is not None:
                reader.close_stream()

        return {
            "code": 200,
            "message": "success",
            "data": {
                "cameraId": _to_number(camera_id),
                "streamUrl": stream_url,
                "processedFrames": len(reports),
                "faceLibrary": face_library_result,
                "reports": reports,
                "reportResponses": report_responses,
            },
        }

    return app


class FaceExtractDetail(BaseModel):
    faceCount: int = 1
    featureVector: list[float] = [0.12, -0.34]
    dimension: int = 512
    qualityScore: float = 0.92
    enrollmentAccepted: bool = True
    faceBox: dict[str, float] | None = None
    modelName: str = "buffalo_l"
    provider: str = "CPUExecutionProvider"
    livenessAvailable: bool = False
    livenessPassed: bool | None = None
    livenessScore: float | None = None
    livenessThreshold: float | None = None
    livenessProvider: str | None = None
    livenessWarning: str | None = None
    qualityHeuristicPassed: bool | None = None
    qualityHeuristicScore: float | None = None
    employeeId: int | str | None = None
    employeeNo: str | None = None
    name: str | None = None
    image: str | None = None


class FaceExtractResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: FaceExtractDetail


app = create_app()


async def _payload(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return {}

    payload = await request.json()
    return payload if isinstance(payload, dict) else {}


async def _read_frame(image: UploadFile | None = None, image_path: str | None = None):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "opencv-python and numpy are required. Run `pip install -r requirements.txt` in ai-service."
        ) from exc

    if image is not None:
        image_bytes = await image.read()
        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Unable to decode uploaded image.")
        return frame

    if not image_path:
        raise ValueError("Provide an uploaded `image` file or an `imagePath`.")

    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Unable to read imagePath: {image_path}")
    return frame


async def _resolve_face_image_source(
    image: UploadFile | None,
    payload: dict,
    image_path_form: str | None,
    image_url_form: str | None,
    image_base64_form: str | None,
):
    if image is not None:
        return await _read_frame(image=image)

    image_source = _first_present(
        payload.get("imageBase64"),
        payload.get("image_base64"),
        image_base64_form,
        payload.get("imageUrl"),
        payload.get("image_url"),
        image_url_form,
        payload.get("imagePath"),
        payload.get("image_path"),
        image_path_form,
        payload.get("photoUrl"),
        payload.get("photo_url"),
        payload.get("image"),
    )
    if not image_source:
        raise ValueError("Provide uploaded `image`, `imageBase64`, `imageUrl`, or `imagePath`.")
    return image_source


def _reload_face_library(payload):
    source = payload.get("source", "local")
    if source == "backend":
        try:
            records = backend_client.list_face_records(status=payload.get("status", "active"))
        except Exception:
            bootstrap = backend_client.get_bootstrap()
            data = bootstrap.get("data", bootstrap) if isinstance(bootstrap, dict) else {}
            records = data.get("employees") if isinstance(data, dict) else []
        return face_service.load_face_library(
            employee_items=records,
            image_base_url=payload.get("imageBaseUrl", Config.FACE_IMAGE_BASE_URL),
            image_dir=payload.get("imageDir", Config.FACE_IMAGE_DIR),
        )

    return face_service.load_face_library(
        records=payload.get("records"),
        employee_items=payload.get("employees"),
        library_path=payload.get("libraryPath", Config.FACE_LIBRARY_PATH),
        image_dir=payload.get("imageDir", Config.FACE_IMAGE_DIR),
        image_base_url=payload.get("imageBaseUrl", Config.FACE_IMAGE_BASE_URL),
    )


def _reload_runtime_cache(payload):
    payload = payload or {}
    source = payload.get("source")
    if source == "backend" or (source is None and not _contains_bootstrap_data(payload)):
        return _bootstrap_from_backend()
    return _apply_bootstrap_payload(payload)


def _bootstrap_from_backend():
    payload = backend_client.get_bootstrap()
    return _apply_bootstrap_payload(payload)


def _start_model_warmup():
    """Warm heavy model runtimes after startup without blocking health checks."""
    thread = threading.Thread(target=_warmup_models, name="ai-model-warmup", daemon=True)
    thread.start()


def _warmup_models():
    started_at = time.perf_counter()
    try:
        import numpy as np

        height = max(64, int(Config.INPUT_HEIGHT or 360))
        width = max(64, int(Config.INPUT_WIDTH or 640))
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        person_detector.detect(frame, frame_id="warmup-person")
        if hasattr(person_detector, "reset_tracks"):
            person_detector.reset_tracks()

        helmet_detector = frame_processor.abnormal_service.helmet_detector
        helmet_detector.detect(frame, person_detections=[], frame_id="warmup-helmet")

        if Config.MODEL_WARMUP_INCLUDE_FACE:
            face_service.recognize(frame, person_detections=[], frame_id="warmup-face")

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info("AI model warmup finished in %.2f ms", elapsed_ms)
    except Exception as exc:
        logger.warning("AI model warmup skipped or failed: %s", exc)


def _apply_bootstrap_payload(payload):
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}

    cache_status = runtime_cache.load_bootstrap(payload)
    face_result = None
    employees = data.get("employees")
    if isinstance(employees, list):
        face_result = face_service.load_face_library(
            employee_items=employees,
            image_base_url=data.get("imageBaseUrl", Config.FACE_IMAGE_BASE_URL),
            image_dir=data.get("imageDir", Config.FACE_IMAGE_DIR),
        )

    return {
        "runtimeCache": cache_status,
        "faceLibrary": face_result or face_service.status(),
    }


def _reload_camera_cache(payload):
    payload = payload or {}
    source = payload.get("source")
    if source == "backend" or (source is None and "cameras" not in payload):
        cameras = backend_client.list_cameras(status=payload.get("status", "online"))
    else:
        cameras = payload.get("cameras") or []
    return runtime_cache.set_cameras(cameras, version=payload.get("version"))


def _reload_zone_cache(payload):
    payload = payload or {}
    source = payload.get("source")
    camera_id = payload.get("cameraId") or payload.get("camera_id")
    if source == "backend" or (source is None and "zones" not in payload):
        zones_by_camera = {}
        camera_ids = payload.get("cameraIds") or payload.get("camera_ids")
        if camera_id not in (None, ""):
            camera_ids = [camera_id]
        if not camera_ids:
            camera_ids = runtime_cache.camera_ids()
        for current_camera_id in camera_ids or []:
            zones_by_camera[current_camera_id] = backend_client.list_zones(current_camera_id)
        status = None
        for current_camera_id, zones in zones_by_camera.items():
            status = runtime_cache.set_zones(zones, camera_id=current_camera_id, version=payload.get("version"))
        return status or runtime_cache.status()

    return runtime_cache.set_zones(
        payload.get("zones") or [],
        camera_id=camera_id,
        version=payload.get("version"),
    )


def _contains_bootstrap_data(payload):
    data = payload.get("data", payload) if isinstance(payload, dict) else {}
    return isinstance(data, dict) and any(key in data for key in ("employees", "cameras", "zones", "settings"))


def _with_playback_url(report, payload):
    enriched = dict(report)
    playback_url = payload.get("playUrl") or payload.get("playbackUrl") or Config.STREAM_PLAY_URL
    if playback_url:
        enriched["playbackUrl"] = playback_url
    return enriched


def _maybe_load_faces_for_stream(payload, include_faces):
    if not include_faces:
        return face_service.status()

    if not _should_load_faces_from_backend(payload):
        return face_service.status()

    force_reload = _to_bool(payload.get("reloadFaces", False))
    if face_service.status().get("loadedFaces", 0) > 0 and not force_reload:
        return face_service.status()

    reload_payload = dict(payload)
    reload_payload["source"] = "backend"
    return _reload_face_library(reload_payload)


def _should_load_faces_from_backend(payload):
    if "loadFacesFromBackend" in payload:
        return _to_bool(payload.get("loadFacesFromBackend"))

    if "faceSource" in payload:
        return payload.get("faceSource") == "backend"

    if not Config.AUTO_LOAD_FACES_FROM_BACKEND:
        return False

    return bool(payload.get("cameraId"))


def _resolve_zones(payload, camera_id):
    zones = payload.get("zones")
    if isinstance(zones, list):
        return zones

    cached_zones = runtime_cache.get_zones(camera_id)
    if cached_zones:
        return cached_zones

    if _to_bool(payload.get("loadZonesFromBackend", False)):
        zones = backend_client.list_zones(camera_id)
        runtime_cache.set_zones(zones, camera_id=camera_id)
        return zones

    return None


def _resolve_stream_source(payload):
    camera_id = payload.get("cameraId")
    stream_url = payload.get("streamUrl")
    if stream_url:
        return stream_url, camera_id

    if not camera_id:
        raise ValueError("Provide `streamUrl` or `cameraId`.")

    camera = runtime_cache.find_camera(camera_id) or backend_client.find_camera(camera_id)
    if not camera:
        raise ValueError(f"Unable to find camera from backend: {camera_id}")

    stream_url = camera.get("streamUrl") or camera.get("stream_url") or camera.get("playUrl") or camera.get("play_url")
    if not stream_url:
        raise ValueError(f"Camera has no streamUrl/playUrl: {camera_id}")
    return stream_url, camera.get("id", camera_id)


def _bounded_frame_count(value):
    try:
        requested = int(value)
    except (TypeError, ValueError):
        requested = 1
    requested = max(1, requested)
    return min(requested, Config.STREAM_MAX_FRAMES_PER_REQUEST)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _to_number(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def _first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _error_response(exc: Exception):
    status_code = 400 if isinstance(exc, ValueError) else 500
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": str(exc), "data": None},
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
    )
