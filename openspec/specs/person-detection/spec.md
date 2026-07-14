# Person Detection

## Purpose

Defines the mandatory person detection and lightweight tracking foundation used by all optional detections.

## Requirements

### Requirement: Detect and track people

AIService SHALL detect people and assign lightweight track identifiers.

#### Scenario: Process video frame

- **GIVEN** a valid frame is available
- **WHEN** person detection runs
- **THEN** YOLO SHALL return person-class detections with bbox and confidence
- **AND** the lightweight tracker SHALL assign a trackId
- **AND** center and foot points SHALL be derived for downstream logic

### Requirement: Person annotation is mandatory

Processed video SHALL retain person detection and green person boxes regardless of optional switches.

#### Scenario: Optional detections are disabled

- **GIVEN** face, helmet, fall, and zone switches are all off
- **WHEN** processed video is produced
- **THEN** person detection SHALL still execute
- **AND** person boxes SHALL remain green in the output stream

### Requirement: Person processing uses latest frames

The person processing loop SHALL consume new frame sequences without stale-frame repetition.

#### Scenario: Inference is slower than input

- **GIVEN** new source frames arrive during inference
- **WHEN** the next analysis iteration begins
- **THEN** it SHALL process the newest frame sequence
- **AND** SHALL NOT repeatedly process the same stale frame after timeout
