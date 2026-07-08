# Abnormal Behavior Recognition

> **Status:** ⚠️ 已更新 —— 反映实际代码实现状态（原 spec 称 YOLO/视频帧读取/推理为 "planned"，实均已实现）

---

## Requirement: Provide Rule-Based Abnormal Behavior Detection

The system SHALL provide rule-based AI service modules for abnormal behavior recognition. Detection SHALL be based on person detection outputs (from YOLO) combined with algorithmic rule checks for zone intrusion, fall, and running. Helmet detection SHALL remain a placeholder pending model integration.

### Scenario: Build AI report payload — [Status: Implemented]

- GIVEN person detections (bbox, trackId, centerPoint, footPoint), camera ID, frame ID, track histories, and warning zone configurations are available
- WHEN `AbnormalBehaviorService.process()` is called with a `FrameContext`
- THEN it SHALL output a payload compatible with `POST /api/ai-results/report/`
- AND the payload SHALL include `cameraId`, `frameId`, `timestamp` and `results` (list of detection result dicts)

### Scenario: Detect warning zone risk by foot point — [Status: Implemented — Algorithmic]

- GIVEN a person detection contains `footPoint: {x, y}`
- AND warning zones contain polygon `points` (or `polygonPoints`) and `safeDistance` (default `0` — no safe margin unless explicitly configured)
- WHEN the foot point is inside the polygon (ray-casting algorithm) or closer than the safe distance to any edge
- THEN the zone detector SHALL output a `ZONE_WARNING` result with `zoneId`, `trackId`, `distance`, and `isInside`

### Scenario: Detect fall risk by continuous bbox ratio — [Status: Implemented — Algorithmic]

- GIVEN a track history contains continuous bbox records for the same `trackId`
- WHEN the bbox width/height ratio exceeds the configured threshold for the configured number of confirm frames
- THEN the fall detector SHALL output a `FALL_ALERT` result with `isFall: true`, `trackId`, and `ratio`

### Scenario: Detect abnormal running by continuous pixel speed — [Status: Implemented — Algorithmic]

- GIVEN a track history contains continuous center points or foot points for the same `trackId`
- WHEN the pixel speed exceeds `RUNNING_SPEED_THRESHOLD` for the configured number of confirm frames
- **⚠️ Known code inconsistency:** The `RunningDetector` class default is `30.0` px/s (`running_detector.py:8`), while the environment-variable-driven config value is `120.0` px/s (`ai_config.py:87` via `RUNNING_SPEED_THRESHOLD`). The runtime-effective value depends on how `app.py` instantiates the detector; this spec does not commit to either number until the engineering team resolves the inconsistency.
- THEN the running detector SHALL output a `RUNNING_ALERT` result with `isRunning: true`, `trackId`, and `speed`

### Scenario: Person detection via YOLO — [Status: Implemented — Code Complete, Pending Model Weights Deployment]

- GIVEN a video frame (640×360, resized from input)
- WHEN `PersonDetector.detect(frame)` is called
- THEN the YOLO model (default: `yolov8n.pt`) SHALL be loaded via `ultralytics.YOLO()`
- AND `model.predict()` SHALL run person-class-only detection (class `[0]`) with configurable confidence (default `0.35`) and IoU (default `0.45`) thresholds
- AND detections SHALL be assigned lightweight track IDs via IoU-based matching (`max_missed_frames=15`)
- AND each detection SHALL return `type: "PERSON_DETECTION"`, `trackId`, `bbox`, `centerPoint`, `footPoint`, `confidence`
- **Note:** Model weight files (`*.pt`) are NOT committed to the repository. Ultralytics auto-downloads `yolov8n.pt` on first run if the local path is absent and the filename matches a known model.

### Scenario: Helmet detection — [Status: Planned / Placeholder]

- GIVEN a person detection exists
- WHEN helmet detection is requested
- THEN the helmet detector SHALL currently return an empty result list (`[]`)
- AND `HelmetDetector.load_model()` SHALL set `self.model = None` (no real model loaded)
- **Planned:** Integrate a real helmet detection model to populate `HELMET_WARNING` results with `helmetStatus` and `confidence`

---

## Detector Implementation Status Summary

| Detector | Type | Implementation | Model Dependency |
|----------|------|---------------|-----------------|
| Person (YOLO) | ML Model | ✅ Complete code | `yolov8n.pt` (auto-download) |
| Zone Warning | Algorithmic | ✅ Fully functional | None |
| Fall Detection | Algorithmic | ✅ Fully functional | None |
| Running Detection | Algorithmic | ✅ Fully functional | None |
| Helmet Detection | ML Model | ❌ Placeholder (`detect()` returns `[]`) | Planned |

---

## Constraints

- AI service SHALL NOT write database directly — it reports structured JSON to `POST /api/ai-results/report/`.
- Person detection code (`PersonDetector`) is fully implemented and wired into the stream processing pipeline. The deployment blocker is purely environmental: model weight files (`*.pt`) must be present at the configured `YOLO_MODEL_PATH` (default `models/yolo/yolov8n.pt`) or auto-downloaded by Ultralytics.
- Fall, running, and zone detectors are algorithmic (no ML model required) and fully functional without any model files.
- Helmet detector (`HelmetDetector`) is a genuine placeholder — `load_model()` sets `model = None` and `detect()` returns `[]`. A real helmet detection model must be integrated separately.
- Max history per track is capped at `MAX_HISTORY_POINTS` (default 5) for the lightweight tracker.
- Detection is throttled to every `FRAME_DETECT_INTERVAL` frames (default 5) in the continuous stream pipeline.

---

## 变更说明

| 变更 | 原 spec | 新草稿 | 依据 |
|------|---------|--------|------|
| 更新 Constraints | "YOLO model loading...remain planned" | 区分代码状态（已实现）vs 部署状态（待权重文件） | `person_detector.py` L53-117; 无 `*.pt` 文件 |
| 新增 YOLO 检测场景 | 无 | PersonDetector + IoU tracker 场景 | `person_detector.py` 全部 |
| 新增安全帽检测场景 | 无 | HelmetDetector placeholder 描述 | `helmet_detector.py` L2, L9-31 |
| 新增检测器状态表 | 无 | 5 个检测器的实现类型与模型依赖 | 逐个 detector 分析 |
| 扩展 Constraints | 3 条 | 6 条：补充 tracker 上限、检测间隔 | `ai_config.py` + 代码分析 |
