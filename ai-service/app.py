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
    abnormal_config={"runningSpeedThreshold": Config.RUNNING_SPEED_THRESHOLD},
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
    input_width=Config.INPUT_WIDTH,
    input_height=Config.INPUT_HEIGHT,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Factory AI Service",
        description="Video-frame analysis, person detection, face recognition, and behavior reporting service.",
        version="0.2.0",
    )

    @app.get("/health", tags=["system"])
    def health_check():
        return {
            "service": Config.SERVICE_NAME,
            "status": "ok",
            "stage": "cuda-yolo-frame-pipeline-ready",
            "docs": "/docs",
            "faceLibrary": face_service.status(),
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

    @app.post("/faces/reload", tags=["faces"])
    async def reload_faces(request: Request):
        try:
            payload = await _payload(request)
            result = _reload_face_library(payload)
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
            zones = _resolve_zones(payload, camera_id)

            reader = StreamReader(
                reconnect_attempts=Config.STREAM_RECONNECT_ATTEMPTS,
                reconnect_delay_seconds=Config.STREAM_RECONNECT_DELAY_SECONDS,
            ).open_stream(stream_url)

            reports = []
            report_responses = []
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

    if _to_bool(payload.get("loadZonesFromBackend", False)):
        return backend_client.list_zones(camera_id)

    return None


def _resolve_stream_source(payload):
    camera_id = payload.get("cameraId")
    stream_url = payload.get("streamUrl")
    if stream_url:
        return stream_url, camera_id

    if not camera_id:
        raise ValueError("Provide `streamUrl` or `cameraId`.")

    camera = backend_client.find_camera(camera_id)
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
