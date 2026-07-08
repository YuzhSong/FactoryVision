from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
import uvicorn

from ai_config import Config
from modules.backend_client import BackendClient
from modules.dependencies import check_dependencies
from modules.face_recognition_service import FaceRecognitionService
from modules.frame_processor import FrameProcessor
from modules.person_detector import PersonDetector
from modules.processed_stream_service import ProcessedStreamService
from modules.runtime_cache import RuntimeCache
from modules.stream_reader import StreamReader


backend_client = BackendClient(
    base_url=Config.BACKEND_API_BASE_URL,
    timeout_seconds=Config.BACKEND_TIMEOUT_SECONDS,
    token=Config.BACKEND_API_TOKEN,
    camera_list_path=Config.BACKEND_CAMERA_LIST_PATH,
    employee_list_path=Config.BACKEND_EMPLOYEE_LIST_PATH,
    face_library_path=Config.BACKEND_FACE_LIBRARY_PATH,
    zone_list_path=Config.BACKEND_ZONE_LIST_PATH,
    ai_report_path=Config.BACKEND_AI_REPORT_PATH,
    bootstrap_path=Config.BACKEND_BOOTSTRAP_PATH,
    realtime_frame_results_path=Config.BACKEND_REALTIME_FRAME_RESULTS_PATH,
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
        "helmetDetectionConfidenceThreshold": Config.HELMET_CONFIDENCE_THRESHOLD,
        "helmetIouThreshold": Config.HELMET_IOU_THRESHOLD,
        "helmetConfidenceThreshold": Config.HELMET_WARNING_THRESHOLD,
        "helmetDevice": Config.HELMET_DEVICE,
        "helmetImageSize": Config.HELMET_IMAGE_SIZE,
        "helmetHalfPrecision": Config.HELMET_HALF_PRECISION,
        "helmetCudnnBenchmark": Config.HELMET_CUDNN_BENCHMARK,
        "fallRatioThreshold": Config.FALL_RATIO_THRESHOLD,
        "fallConfirmFrames": Config.FALL_CONFIRM_FRAMES,
        "fallMinConfidence": Config.FALL_MIN_CONFIDENCE,
        "fallPoseHorizontalAngleThreshold": Config.FALL_POSE_HORIZONTAL_ANGLE_THRESHOLD,
        "fallPoseMinKeypointConfidence": Config.FALL_POSE_MIN_KEYPOINT_CONFIDENCE,
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
    default_report_realtime_to_backend=Config.STREAM_REPORT_REALTIME_TO_BACKEND,
    reconnect_attempts=Config.STREAM_RECONNECT_ATTEMPTS,
    reconnect_delay_seconds=Config.STREAM_RECONNECT_DELAY_SECONDS,
    output_fps=Config.STREAM_OUTPUT_FPS,
    ffmpeg_path=Config.STREAM_FFMPEG_PATH,
    detect_interval=Config.FRAME_DETECT_INTERVAL,
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

    @app.on_event("startup")
    def bootstrap_runtime_cache_on_startup():
        if Config.BOOTSTRAP_ON_STARTUP:
            try:
                _bootstrap_from_backend()
            except Exception as exc:
                runtime_cache.set_error(exc)

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

    @app.post("/faces/extract", tags=["faces"])
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
            stream_url, camera_id = _resolve_stream_source(payload)
            max_frames = _bounded_frame_count(payload.get("maxFrames", 1))
            sample_interval = int(payload.get("sampleInterval", Config.STREAM_SAMPLE_INTERVAL) or 1)
            include_faces = _to_bool(payload.get("includeFaces", True))
            face_library_result = _maybe_load_faces_for_stream(payload, include_faces)
            report_to_backend = _to_bool(payload.get("reportToBackend", False))
            report_realtime_to_backend = _to_bool(payload.get("reportRealtimeToBackend", False))
            zones = _resolve_zones(payload, camera_id)

            reader = StreamReader(
                reconnect_attempts=Config.STREAM_RECONNECT_ATTEMPTS,
                reconnect_delay_seconds=Config.STREAM_RECONNECT_DELAY_SECONDS,
            ).open_stream(stream_url)

            reports = []
            report_responses = []
            realtime_report_responses = []
            for packet in reader.iter_frames(max_frames=max_frames, sample_interval=sample_interval):
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
                    report_responses.append(backend_client.report_ai_results(report))
                if report_realtime_to_backend:
                    realtime_report_responses.append(
                        backend_client.report_realtime_frame_results(_with_playback_url(report, payload))
                    )
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
                "realtimeReportResponses": realtime_report_responses,
            },
        }

    return app


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
        records = backend_client.list_face_records(status=payload.get("status", "active"))
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
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc), "data": None},
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
    )
