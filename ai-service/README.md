# AI Service

FastAPI-based AI service for smart factory video-frame analysis. This service consumes camera stream URLs or uploaded images, runs CUDA-accelerated YOLO person detection, optionally runs InsightFace employee recognition, draws detection boxes with OpenCV, pushes processed RTMP video back to SRS through FFmpeg, and reports structured AI results to the backend API.

## Boundary

- `ai-service` reads frames from a provided `streamUrl` or local video path.
- `ai-service` can pull raw RTMP from SRS and push an AI processed RTMP stream back to SRS.
- `ai-service` does not implement SRS, camera pushing, or database writes.
- Employee, camera, zone, and AI-result integration should go through backend HTTP APIs.

## Current Status

Implemented on the AI side:

- Person detection: `PERSON_DETECTION`.
- Face recognition, face feature extraction, face-library reload, and employee cache upsert/delete.
- Basic RGB liveness detection for static-image and flat-photo spoof defense.
- Stranger confirmation alert: `STRANGER_ALERT`.
- Helmet violation alert: `HELMET_WARNING`.
- Dangerous-zone alert after entering/near-edge stay, default 10 seconds: `ZONE_WARNING`.
- Fall alert with pose keypoints first and bbox fallback: `FALL_ALERT`.
- Running alert based on per-track pixel speed: `RUNNING_ALERT`.
- Employee leave/return event: `EMPLOYEE_PRESENCE_EVENT`.
- Event media recording for alert keyframes and short replay clips.

Known gaps outside or beyond the current AI implementation:

- Frontend polygon-zone drawing and backend zone persistence are not complete.
- Backend face enrollment -> AI feature extraction -> feature persistence -> AI cache refresh is not complete.
- Backend alert persistence, alert handling, DingTalk notification, and escalation are not complete.
- Video replay and AI face-swap spoof defense are not complete; current liveness is only a basic RGB first stage.
- Realtime structured annotation WebSocket is not complete. Realtime video display currently uses processed video stream playback.

Event classification:

- AI-service only emits machine-readable `category`: `abnormal_behavior` or `emergency_event`.
- AI-service does not emit frontend display colors. Django/Vue should decide how to color alert rows based on `type` or `category`.

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
.\.venv\Scripts\python.exe -m compileall app.py ai_config.py modules scripts
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Endpoints

- `GET /health`: service status and face-library status.
- `GET /docs`: Swagger UI.
- `GET /openapi.json`: OpenAPI schema.
- `GET /dependencies`: Python package and CUDA availability check.
- `GET /faces/status`: current InsightFace library/model status.
- `POST /faces/extract`: extract one employee face embedding from upload, image URL, base64, or local path.
- `POST /faces/reload`: load employees from local JSON/images or backend.
- `GET /cache/status`: current runtime cache and face-library status.
- `POST /cache/reload`: reload runtime cache from backend bootstrap or provided payload.
- `POST /cache/employees/upsert`: add or replace employee face records in AI memory.
- `POST /cache/employees/delete`: remove employee face records from AI memory.
- `POST /cache/cameras/reload`: reload camera config cache.
- `POST /cache/zones/reload`: reload zone config cache.
- `POST /detect/person`: uploaded image or `imagePath`, returns `PERSON_DETECTION`.
- `POST /detect/frame`: uploaded image or `imagePath`, returns combined AI report.
- `POST /process/stream`: process a limited number of frames from `streamUrl` or backend camera config. When `cameraId` and face recognition are enabled, it loads employee face records from backend by default. Set `reportRealtimeToBackend=true` to post frame-level results to the backend realtime endpoint.
- `POST /streams/start`: start continuous RTMP input -> AI boxed RTMP output processing. Set `reportRealtimeToBackend=true` to report frame-level results for WebSocket broadcast.
- `POST /streams/stop`: stop continuous processed stream output.
- `GET /streams/status`: current processed stream task status.

## Processed Stream Demo

Default demo flow:

```text
rtmp://81.70.90.222:1935/live/1
  -> AI Service
  -> rtmp://81.70.90.222:1935/live/1_detected
  -> https://webrtc.rainycode.cn:8443/live/1_detected.flv
```

The continuous processed stream is optimized for real-time playback rather than
processing every old frame. It uses two loops:

- Capture loop: continuously reads the raw RTMP stream and overwrites one
  `latest_frame` slot.
- Process loop: copies only the newest available frame, processes it, draws
  boxes/metrics, and pushes it to `rtmp://81.70.90.222:1935/live/1_detected`.

If processing is slower than capture, old unprocessed frames are dropped. This
prevents the processed stream from drifting tens of seconds behind the phone
camera. The service exposes `dropped_frames`, `capture_fps`, `process_fps`,
`process_time_ms`, `latest_frame_age_ms`, and `output_fps` from
`GET /streams/status`, and overlays the same live debug data on the video.

Detection does not have to run on every output frame. By default the service
runs heavier detection every 5 input frames and reuses the latest detection
result for intermediate frames, so the output stream can continue while latency
stays bounded.

Behavior algorithms can still keep lightweight history. `FrameProcessor` stores
only recent structured track points per `trackId`:

```python
track_history = {
    "t-1": [
        {
            "timestamp": "2026-07-08T03:00:00+08:00",
            "center": [120.0, 240.0],
            "bbox": [100.0, 120.0, 240.0, 360.0],
        }
    ]
}
```

Each track keeps only the latest `MAX_HISTORY_POINTS` entries. Full frames and
image queues are not stored for speed, running, fall, or zone logic.

Use `mode=test` first to verify the whole stream path with a synthetic box:

```powershell
curl -X POST http://127.0.0.1:9000/streams/start `
  -H "Content-Type: application/json" `
  -d "{\"mode\":\"test\"}"
```

Switch to detection mode after the stream path is stable:

```powershell
curl -X POST http://127.0.0.1:9000/streams/start `
  -H "Content-Type: application/json" `
  -d "{\"mode\":\"detect\",\"includeFaces\":false}"
```

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
- `FACE_MIN_SCORE_MARGIN`: default `0.03`; reject matches when best and second-best employee scores are too close.
- `FACE_MIN_SAMPLES_PER_EMPLOYEE`: default `2`; employees below this sample count use a stricter threshold.
- `FACE_SPARSE_SAMPLE_THRESHOLD_PENALTY`: default `0.03`; extra threshold added for sparse employee samples.
- `FACE_ENROLLMENT_MIN_QUALITY_SCORE`: default `0.5`; reject low-confidence enrollment faces when detector score is available.
- `FACE_ENROLLMENT_MIN_FACE_SIZE`: default `40`; reject enrollment faces whose smaller bbox side is below this pixel size.
- `FACE_ENROLLMENT_MAX_POSE_YAW`: default `75`; reject enrollment faces with excessive yaw when pose metadata is available.
- `FACE_LIVENESS_ENABLED`: default `True`; run passive RGB liveness before accepting realtime face matches.
- `FACE_LIVENESS_THRESHOLD`: default `0.55`; minimum liveness score required for realtime face recognition.
- `FACE_LIVENESS_MIN_FACE_SIZE`: default `48`; minimum face crop side for liveness evaluation.
- `FACE_LIVENESS_MODEL_PATH`: optional ONNX anti-spoofing model path; when absent, RGB heuristics are used.
- `FACE_LIVENESS_REQUIRE_FOR_ENROLLMENT`: default `False`; when `True`, reject `/faces/extract` enrollment images that fail liveness.
- `AUTO_LOAD_FACES_FROM_BACKEND`: default `True` for `cameraId` stream processing.
- `BACKEND_API_BASE_URL`: default `http://127.0.0.1:8000/api`.
- `BACKEND_CAMERA_LIST_PATH`: default `/cameras/list/`.
- `BACKEND_EMPLOYEE_LIST_PATH`: default `/employees/list/`.
- `BACKEND_ZONE_LIST_PATH`: default `/zones/`.
- `BACKEND_AI_REPORT_PATH`: default `/ai-results/report/`.
- `BACKEND_BOOTSTRAP_PATH`: default `/ai/bootstrap/`.
- `BACKEND_REALTIME_FRAME_RESULTS_PATH`: default `/realtime/frame-results/`.
- `BOOTSTRAP_ON_STARTUP`: default `False`; when `True`, fetch backend bootstrap data at FastAPI startup.
- `STREAM_MAX_FRAMES_PER_REQUEST`: safety limit for `/process/stream`.
- `STREAM_INPUT_URL`: default `rtmp://81.70.90.222:1935/live/1`.
- `STREAM_OUTPUT_URL`: default `rtmp://81.70.90.222:1935/live/1_detected`.
- `STREAM_PLAY_URL`: default `webrtc://webrtc.rainycode.cn:8443/live/1_detected`.
- `STREAM_PROCESS_MODE`: `test` or `detect`, default `detect`.
- `STREAM_REPORT_REALTIME_TO_BACKEND`: default `False`; when `True`, continuous stream tasks post frame-level results to `BACKEND_REALTIME_FRAME_RESULTS_PATH`.
- `STREAM_FFMPEG_PATH`: default `ffmpeg`; required for `/streams/start`.
- `OUTPUT_FPS` / `STREAM_OUTPUT_FPS`: default `10`.
- `FRAME_DETECT_INTERVAL`: default `5`; run heavier detection every N input frames.
- `EVENT_MEDIA_ENABLED`: default `True`; save alert keyframes and short event clips during continuous stream processing.
- `EVENT_MEDIA_DIR`: default `data/event_media`; local directory for event keyframes, clips, and manifests.
- `EVENT_MEDIA_PRE_SECONDS`: default `3`; seconds of buffered frames to include before an event.
- `EVENT_MEDIA_POST_SECONDS`: default `3`; seconds of frames to append after an event.
- `EVENT_MEDIA_COOLDOWN_SECONDS`: default `10`; suppress repeated media bundles for the same event signature.
- `MAX_HISTORY_POINTS`: default `5`; per-track lightweight history length.
- `INPUT_WIDTH`: default `640`; resize continuous-stream frames before processing.
- `INPUT_HEIGHT`: default `360`; resize continuous-stream frames before processing.
- `RUNNING_SPEED_THRESHOLD`: default `120.0`; pixel/second threshold for running alerts.
- `ZONE_MIN_STAY_SECONDS`: default `10`; person must stay inside or within safe distance this long before `ZONE_WARNING`.
- `ZONE_STATE_TTL_SECONDS`: default `30`; clear stale zone stay state after inactivity.
- `FALL_RATIO_THRESHOLD`: default `1.2`; bbox width/height fallback threshold for fall-like posture.
- `FALL_CONFIRM_FRAMES`: default `5`; consecutive recent fall-like frames required before `FALL_ALERT`.
- `FALL_MIN_CONFIDENCE`: default `0.6`; minimum confidence for high-level fall alerts.
- `FALL_POSE_HORIZONTAL_ANGLE_THRESHOLD`: default `35`; body shoulder-to-hip angle from horizontal for pose-based fall detection.
- `FALL_POSE_MIN_KEYPOINT_CONFIDENCE`: default `0.3`; minimum usable pose keypoint confidence.
- `EMPLOYEE_ABSENCE_TIMEOUT_SECONDS`: default `60`; mark a recognized employee absent after this many seconds without a matched face.
- `EMPLOYEE_PRESENCE_MIN_SIMILARITY`: default `0`; optional minimum face similarity required before updating presence state.
- `STRANGER_CONFIRM_FRAMES`: default `3`; consecutive unknown-face observations required before `STRANGER_ALERT`.
- `STRANGER_COOLDOWN_SECONDS`: default `30`; suppress repeated stranger alerts for the same approximate face location.
- `STRANGER_MATCH_DISTANCE_THRESHOLD`: default `80`; pixel distance used to associate unknown faces across frames.
- `STRANGER_STATE_TTL_SECONDS`: default `10`; remove stale unknown-face confirmation state after inactivity.
