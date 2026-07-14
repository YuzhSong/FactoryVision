# AI Results Reporting

## Purpose

Defines how AIService reports detections, persists formal events, applies event policies, and attaches replay evidence without blocking real-time processing.

## Requirements

### Requirement: AI detection result reporting

The Backend SHALL validate AI reports and persist each accepted result as a formal `events.Event`. Alert-class results SHALL create an `Alert` linked through `Alert.event`; no `AIEvent` compatibility model SHALL be used.

#### Scenario: Report detection results

- **GIVEN** AIService produced a frame report
- **WHEN** it calls `POST /api/ai-results/report/` with `cameraId`, `timestamp`, and `results`
- **THEN** Backend SHALL validate the camera and result payloads
- **AND** SHALL return accepted/rejected counts, `eventIds`, `alertIds`, `cameraId`, and `frameId`
- **AND** SHALL NOT return AIEvent identifiers

#### Scenario: Person observation does not create an alert

- **GIVEN** an accepted result is a non-alert person observation
- **WHEN** Backend persists it
- **THEN** one `Event` SHALL be created
- **AND** no `Alert` SHALL be created

### Requirement: AI events shall be deduplicated by event policy

Actionable results SHALL be accepted at most once per relevant camera, region, track, event type, and cooldown window.

#### Scenario: Region intrusion policy

- **GIVEN** the same region intrusion was accepted inside its cooldown window
- **WHEN** a duplicate is reported
- **THEN** the duplicate SHALL be rejected
- **AND** accepted intrusion events SHALL default to medium severity

#### Scenario: Region dwell policy

- **GIVEN** the same region dwell was accepted inside its longer cooldown window
- **WHEN** a duplicate is reported
- **THEN** the duplicate SHALL be rejected
- **AND** accepted dwell events SHALL default to high severity

### Requirement: Report replay evidence

Actionable events SHALL include bounded evidence when available.

#### Scenario: Preserve trajectory and context

- **GIVEN** AIService has recent track, region, bbox, or trigger data
- **WHEN** an actionable result is reported
- **THEN** evidence SHALL be bounded and stored in `Event.payload`
- **AND** raw frame image data SHALL NOT be embedded in the JSON payload

### Requirement: Upload event replay media

AIService SHALL upload completed keyframes and clips after Backend accepts the event.

#### Scenario: Upload media

- **GIVEN** a formal Event exists
- **WHEN** AIService posts multipart data to `POST /api/events/{eventId}/media/`
- **THEN** Backend SHALL save the files and update `Event.payload.media` with browser-accessible URLs
- **AND** SHALL synchronize the alert snapshot path when a keyframe is uploaded

#### Scenario: Keep media work off the frame path

- **GIVEN** media encoding or upload is slow or fails
- **WHEN** AIService is processing live video
- **THEN** media work SHALL run through a bounded background queue
- **AND** SHALL NOT block frame processing or invalidate the accepted event

### Requirement: Event replay clips shall be browser playable

AIService SHALL encode replay clips in a browser-playable format when FFmpeg is available.

#### Scenario: Generate replay clip

- **GIVEN** FFmpeg is available
- **WHEN** an event clip is finalized
- **THEN** it SHALL use H.264 MP4 with yuv420p and browser-oriented metadata
- **AND** failures SHALL fall back to keyframe or manifest evidence

### Requirement: Runtime media shall not be committed

Generated runtime media SHALL remain outside version control.

#### Scenario: Inspect repository changes

- **GIVEN** keyframes, clips, manifests, or fallback frames were generated
- **WHEN** Git status is inspected
- **THEN** those runtime artifacts SHALL remain ignored
