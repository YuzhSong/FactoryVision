# AI Service

FastAPI-based AI service for smart factory video-frame analysis. This service consumes camera stream URLs or uploaded images, runs CUDA-accelerated YOLO person detection, optionally runs InsightFace employee recognition, and reports structured AI results to the backend API.

## Boundary

- `ai-service` reads frames from a provided `streamUrl` or local video path.
- `ai-service` does not implement MediaMTX, Nginx-RTMP, camera pushing, stream forwarding, or database writes.
- Employee, camera, zone, and AI-result integration should go through backend HTTP APIs.

## Quick Start

```powershell
cd ai-service
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-cuda.txt
uvicorn app:app --host 0.0.0.0 --port 9000 --reload
```

The CUDA requirements install PyTorch wheels for CUDA 12.8. On an RTX 4060 environment, `YOLO_DEVICE=auto` should resolve to `cuda:0`.

## Checks

```powershell
.\.venv\Scripts\python.exe .\scripts\check_cuda_yolo.py
.\.venv\Scripts\python.exe -m compileall app.py config.py modules scripts
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Endpoints

- `GET /health`: service status and face-library status.
- `GET /docs`: Swagger UI.
- `GET /openapi.json`: OpenAPI schema.
- `GET /dependencies`: Python package and CUDA availability check.
- `GET /faces/status`: current InsightFace library/model status.
- `POST /faces/reload`: load employees from local JSON/images or backend.
- `POST /detect/person`: uploaded image or `imagePath`, returns `PERSON_DETECTION`.
- `POST /detect/frame`: uploaded image or `imagePath`, returns combined AI report.
- `POST /process/stream`: process a limited number of frames from `streamUrl` or backend camera config. When `cameraId` and face recognition are enabled, it loads employee face records from backend by default.

## Face Library

Local JSON path defaults to `data/faces/face_library.json`. It can contain either feature vectors or image paths:

```json
{
  "items": [
    {
      "employeeId": 1,
      "employeeNo": "E001",
      "name": "Zhang San",
      "featureVector": [0.01, 0.02]
    },
    {
      "employeeId": 2,
      "employeeNo": "E002",
      "name": "Li Si",
      "imagePath": "employees/2_E002_LiSi/photo.jpg"
    }
  ]
}
```

Local employee image directory defaults to `data/faces/employees`. A practical layout is one folder per employee, for example `data/faces/employees/1_E001_ZhangSan/*.jpg`.

When loading from backend with `POST /faces/reload` and `{"source": "backend"}`, the service reads `/api/employees/list/` by default. Each employee item may include `faceFeatures`, `faces`, `photos`, or `images`. A face item may provide `featureVector`/`feature_vector` directly, or an image field such as `imagePath`, `photoUrl`, or `imageBase64`.

For camera processing, `POST /process/stream` automatically uses the same backend employee data when the request contains `cameraId`. Set `loadFacesFromBackend=false` for local stream tests that should not call the backend employee API.

## Key Environment Variables

- `YOLO_MODEL_PATH`: default `models/yolo/yolov8n.pt`.
- `YOLO_DEVICE`: `auto`, `cuda:0`, or `cpu`.
- `YOLO_IMAGE_SIZE`: default `640`, lower is faster and less precise.
- `YOLO_HALF_PRECISION`: default `auto`, enables FP16 only on CUDA.
- `FACE_PROVIDER`: `auto`, `cuda`, or `cpu`. CUDA requires `onnxruntime-gpu`.
- `FACE_LIBRARY_PATH`: local face library JSON path.
- `FACE_IMAGE_DIR`: local employee image directory.
- `AUTO_LOAD_FACES_FROM_BACKEND`: default `True` for `cameraId` stream processing.
- `BACKEND_API_BASE_URL`: default `http://127.0.0.1:8000/api`.
- `BACKEND_CAMERA_LIST_PATH`: default `/cameras/list/`.
- `BACKEND_EMPLOYEE_LIST_PATH`: default `/employees/list/`.
- `BACKEND_ZONE_LIST_PATH`: default `/zones/`.
- `BACKEND_AI_REPORT_PATH`: default `/ai-results/report/`.
- `STREAM_MAX_FRAMES_PER_REQUEST`: safety limit for `/process/stream`.
