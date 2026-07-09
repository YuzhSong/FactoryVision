# Face Recognition

> **Status:** ⚠️ 已更新 —— AI 服务已实现完整 InsightFace 推理管线（原 spec 称 "placeholder classes and methods"）

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Face Recognition in the Factory Vision system.
## Requirements
### Requirement: Face Recognition Service

The system SHALL provide an AI-side face recognition service using InsightFace for face detection and feature extraction, with cosine similarity matching against a configurable face library. The service SHALL remain independent from the backend database implementation.

#### Scenario: Load face recognition model — [Status: Implemented]

- GIVEN the `FaceRecognitionService` is instantiated with model name `"buffalo_l"` (default) and model root path from `INSIGHTFACE_HOME` env var
- WHEN `_load_model()` is called (lazy-loaded on first use)
- THEN the InsightFace `FaceAnalysis` model SHALL be initialized with detection size `(640, 640)` and the configured provider (`"auto"` by default, resolving to CUDA or CPU)
- AND the model SHALL be ready for face detection and feature extraction

#### Scenario: Load face library from backend or local sources — [Status: Implemented]

- GIVEN a `BackendClient` is configured with a face library path
- WHEN `load_face_library(source="backend")` is called
- THEN the service SHALL call `BackendClient.list_face_records()` to fetch employee face data from the backend
- AND if no face-specific data is returned, it SHALL fall back to `list_employees()` for employee items
- AND each employee item with nested `faceFeatures` SHALL be expanded into individual `FaceRecord` entries
- AND face records may alternatively be loaded from a local JSON file (`library_path`) or image directory (`image_dir`)
- **Note:** Backend has no dedicated face API endpoint — the `list_employees()` fallback is the currently effective data path. A future `/face/` endpoint should be added to serve face records directly.

#### Scenario: Match detected face against face library — [Status: Implemented]

- GIVEN a query face's normalized feature vector and a loaded face library
- WHEN `_match(feature)` is called
- THEN the service SHALL compute cosine similarity (`np.dot`) between the query feature and each stored `FaceRecord.feature`
- AND SHALL return the `FaceRecord` with the highest similarity score
- AND if the highest similarity is below `FACE_SIMILARITY_THRESHOLD` (default `0.45`), the match SHALL be discarded

#### Scenario: Recognize faces in a frame — [Status: Implemented]

- GIVEN a video frame and a list of person detections (with bounding boxes)
- WHEN `recognize(frame, person_detections, frame_id, timestamp)` is called
- THEN the service SHALL detect all faces in the frame using InsightFace
- AND SHALL assign each detected face to a person detection by point-containment + IoU scoring
- AND SHALL match each assigned face against the face library
- AND SHALL return a list of `FACE_RESULT` dicts containing `trackId`, `employeeId`, `employeeNo`, `employeeName`, `similarity`, and `bbox`

#### Scenario: Extract face feature from an image — [Status: Implemented]

- GIVEN an image (file path, base64 string, URL, or numpy array)
- WHEN `extract_feature(image)` is called
- THEN the service SHALL return a normalized 512-dimensional face embedding vector
- AND the vector norm SHALL be 1.0 (L2-normalized)
- AND supported image formats SHALL be: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.webp` (`SUPPORTED_IMAGE_SUFFIXES` in `face_recognition_service.py:8`)
- AND HTTP image loading SHALL use a timeout of `10` seconds (`face_recognition_service.py:306`)

#### Scenario: Query face service status — [Status: Implemented]

- GIVEN the face service is initialized
- WHEN `GET /faces/status` is called on the AI service
- THEN the response SHALL include model name, model loaded status, face library size, and similarity threshold

#### Scenario: Reload face library — [Status: Implemented]

- GIVEN the face service is running
- WHEN `POST /faces/reload` is called
- THEN the service SHALL reload the face library from the configured backend source

---

### Requirement: Backend face enrollment API

The system SHALL accept employee face enrollment through a backend API that receives exactly three face images for one employee.

#### Scenario: Enroll three face images

- **GIVEN** a valid JWT access token and an existing employee
- **WHEN** `POST /api/face/enroll/` is called with `employeeId` and `faces`
- **THEN** `faces` SHALL contain exactly three items
- **AND** each item SHALL contain `imageBase64` and `faceType`
- **AND** the allowed `faceType` values SHALL be `front`, `left`, and `right`
- **AND** the response SHALL return `results` with `faceType` and `faceFeatureId` for each saved face feature

#### Scenario: Reject incomplete face enrollment

- **GIVEN** the request body contains fewer or more than three face images
- **WHEN** `POST /api/face/enroll/` is called
- **THEN** the backend SHALL reject the request with a validation error

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Face Recognition in the Factory Vision system.

## Planned Features (Not Yet Implemented)

- [ ] **Backend face API:** No `/face/enroll/` or face data endpoints exist in `backend/apps/` — only a stub `faceApi.enroll()` in frontend
- [ ] **Frontend face management UI:** No face enrollment or face library browsing page
- [ ] **Face image persistence:** Face images are not stored or served by the backend

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Face Recognition in the Factory Vision system.

## Constraints

- The face recognition service SHALL NOT write to the database directly — it communicates with the backend only through `BackendClient`.
- Face records (`FaceRecord`) hold `employee_id`, `employee_no`, `name`, `feature` (numpy array), and `source`.
- The service supports multiple input sources: direct records dict, employee items list, JSON file, and image directory — with local file paths taking precedence over remote image URLs.
- `InsightFace` library auto-downloads the `buffalo_l` model package on first run. The model cache directory is controlled by `INSIGHTFACE_HOME` env var (default: `models/insightface`).

---

## Purpose
Defines the expected behavior, constraints, and acceptance scenarios for Face Recognition in the Factory Vision system.

## 变更说明

| 变更 | 原 spec | 新草稿 | 依据 |
|------|---------|--------|------|
| 替换 placeholder 描述 | "placeholder classes and methods" | 6 个具体 Scenario + 算法细节 | `face_recognition_service.py` 全部 616 行 |
| 新增模型加载场景 | 无 | InsightFace `buffalo_l` + lazy loading | `face_recognition_service.py` L253-327 |
| 新增余弦相似度匹配 | 无 | `np.dot` on normalized vectors, threshold 0.45 | `face_recognition_service.py` L329-344 |
| 新增人脸库加载场景 | 无 | BackendClient + employee items fallback | `face_recognition_service.py` L50-82 |
| 新增帧识别场景 | 无 | face detection + person assignment + matching | `face_recognition_service.py` L84-130 |
| 新增 API 端点场景 | 无 | /faces/status, /faces/reload | `ai-service/app.py` L119-128 |
| 保留 Constraints | 原有一条 | 扩展为 4 条具体约束 | 代码分析 |
| 新增 Planned Features | 无 | 后端/前端人脸 API 仍为 stub | `backend/apps/` 搜索结果为空 |
