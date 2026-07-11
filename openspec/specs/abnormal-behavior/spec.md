# Abnormal Behavior Recognition

> **Status:** Implemented for person detection, zone warning, fall detection, and running detection. Helmet detection remains model-dependent.

## Purpose

Defines the expected behavior, constraints, and acceptance scenarios for abnormal behavior recognition in the Factory Vision system.

## Requirements

### Requirement: Provide rule-based abnormal behavior detection

The AI service SHALL provide abnormal behavior recognition based on person detection outputs and lightweight track histories. The currently implemented behavior detectors include zone warning, fall detection, running detection, stranger detection, employee presence events, and model-dependent helmet warning.

#### Scenario: Build AI report payload — [Status: Implemented]

- GIVEN person detections with `bbox`, `trackId`, `centerPoint`, and `footPoint`
- AND camera ID, frame ID, timestamp, track histories, and warning zone configurations are available
- WHEN `FrameProcessor.process_frame()` is called
- THEN it SHALL return a payload compatible with `POST /api/ai-results/report/`
- AND the payload SHALL include `cameraId`, `frameId`, `timestamp`, and `results`.

#### Scenario: Detect warning zone risk by foot point — [Status: Implemented]

- GIVEN a person detection contains `footPoint: {x, y}`
- AND warning zones contain polygon `points` or `polygonPoints`
- WHEN the foot point is inside the polygon or near the zone boundary within the configured safe distance
- THEN the zone detector SHALL output a `ZONE_WARNING` result with zone, track, distance, and level information.

#### Scenario: Detect fall risk by continuous pose or bbox history — [Status: Implemented]

- GIVEN a track history contains continuous records for the same `trackId`
- AND records may contain pose keypoints, bbox, timestamp, frame index, and fps
- WHEN pose keypoints are available with usable shoulder and hip points
- THEN the fall detector SHALL use body angle from horizontal as the primary fall evidence
- WHEN pose keypoints are unavailable or below confidence threshold
- THEN the fall detector SHALL fall back to bbox width/height ratio
- AND when fall-like evidence is present for the configured number of confirm frames
- THEN the fall detector SHALL output a `FALL_ALERT` result with `isFall: true`, `trackId`, `confidence`, `durationFrames`, `evidenceType`, `evidence`, and `level`
- AND `FrameProcessor` SHALL include that result in the AI report payload
- AND the backend SHALL create an `Event` and an `Alert` after receiving `FALL_ALERT` through `/api/ai-results/report/`.

#### Scenario: Detect abnormal running by continuous pixel speed — [Status: Implemented]

- GIVEN a track history contains continuous center points for the same `trackId`
- WHEN the pixel speed exceeds the configured running threshold for the configured number of confirm frames
- THEN the running detector SHALL output a `RUNNING_ALERT` result with running state, track, speed, duration, and level information.

#### Scenario: Person detection via YOLO — [Status: Implemented, model file required or auto-download]

- GIVEN a video frame
- WHEN `PersonDetector.detect(frame)` is called
- THEN the YOLO model SHALL run person-class-only detection with configurable confidence and IoU thresholds
- AND detections SHALL be assigned lightweight track IDs via IoU-based matching
- AND each detection SHALL return `PERSON_DETECTION`, `trackId`, `bbox`, `centerPoint`, `footPoint`, and `confidence`.

#### Scenario: Helmet detection — [Status: Model-dependent]

- GIVEN a helmet model is available at the configured path or through the selected provider
- WHEN helmet detection is requested
- THEN the detector SHALL attempt to classify helmet status for detected persons
- AND `HELMET_WARNING` SHALL be generated for no-helmet conditions.

## Detector Implementation Status Summary

| Detector | Type | Implementation | Model Dependency |
| --- | --- | --- | --- |
| Person detection | ML model | Implemented | YOLO model file or Ultralytics auto-download |
| Zone warning | Algorithmic | Implemented | None |
| Fall detection | Algorithmic | Implemented | None |
| Running detection | Algorithmic | Implemented | None |
| Helmet detection | ML model | Partially implemented | Helmet model required for production use |

## Constraints

- AI service SHALL NOT write database directly; it reports structured JSON to `POST /api/ai-results/report/`.
- Fall, running, and zone detectors are algorithmic and do not require dedicated model files.
- Fall detection accuracy improves when upstream person detection provides pose keypoints; otherwise bbox ratio is used as fallback.
- Max history per track is capped by `MAX_HISTORY_POINTS`.
- Continuous stream detection is throttled by `FRAME_DETECT_INTERVAL`.
- Backend `FALL_ALERT` handling creates both `Event` and `Alert` records.

## Change Notes

| Change | Basis |
| --- | --- |
| Clarified fall detection as delivered feature | `fall_detector.py`, `frame_processor.py`, `abnormal_behavior_service.py`, AI and backend tests |
| Documented pose-first and bbox-fallback fall strategy | `FallDetector._pose_fall_score()` and `_bbox_fall_score()` |
| Documented backend alert closure for `FALL_ALERT` | `backend/apps/ai_results/views.py` and `tests.py` |
