# Abnormal Behavior Recognition

## Requirement: Provide Rule-Based Abnormal Behavior Detection

The system SHALL provide rule-based AI service modules for abnormal behavior recognition before production model inference is integrated.

### Scenario: Build AI report payload

- GIVEN person detections, camera ID, frame ID, track histories and warning zone configurations are available
- WHEN the abnormal behavior service processes the frame context
- THEN it SHALL output a payload compatible with `POST /api/ai-results/report/`
- AND the payload SHALL include `cameraId`, `frameId`, `timestamp` and `results`

### Scenario: Detect warning zone risk by foot point

- GIVEN a person detection contains `footPoint`
- AND warning zones contain polygon `points` and `safeDistance`
- WHEN the foot point is inside the polygon or closer than the safe distance
- THEN the zone detector SHALL output a `ZONE_WARNING` result

### Scenario: Detect fall risk by continuous bbox ratio

- GIVEN a track history contains continuous bbox records for the same `trackId`
- WHEN the bbox width-height ratio exceeds the threshold for configured confirm frames
- THEN the fall detector SHALL output a `FALL_ALERT` result with `isFall=true`

### Scenario: Detect abnormal running by continuous pixel speed

- GIVEN a track history contains continuous center points or foot points for the same `trackId`
- WHEN the pixel speed exceeds the configured threshold for configured confirm frames
- THEN the running detector SHALL output a `RUNNING_ALERT` result with `isRunning=true`

## Constraints

- AI service SHALL NOT write database directly.
- AI service SHALL report structured JSON to backend API.
- YOLO model loading, real video frame reading and production inference remain planned until model files and runtime environment are confirmed.
