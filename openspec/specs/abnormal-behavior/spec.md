# Safety and Abnormal Behavior Detection

## Purpose

Defines safety helmet, fall, running, and warning-zone detection built on tracked person detections.

## Requirements

### Requirement: Selectable safety detections

AIService SHALL always execute person detection and SHALL execute optional safety detections only when enabled.

#### Scenario: Start processed stream

- **GIVEN** a stream start request includes optional detection switches
- **WHEN** AIService begins processing
- **THEN** person detection SHALL always run
- **AND** face, helmet, fall, and zone detection SHALL only run when their switch is enabled

### Requirement: Helmet state shall remain visually stable

AIService SHALL persist matched helmet presentation briefly so transient misses do not cause flicker.

#### Scenario: Display helmet state

- **GIVEN** a helmet/no_helmet detection is matched to a person track
- **WHEN** later frames temporarily miss the helmet or person detection
- **THEN** AIService SHALL retain the matched head state for the configured short TTL
- **AND** SHALL reproject the relative head box onto the latest person box
- **AND** the person box SHALL remain green
- **AND** Helmet SHALL use a green/teal head box while No Helmet SHALL use red

#### Scenario: Report no-helmet event

- **GIVEN** a fresh no_helmet detection is matched to a person
- **WHEN** event cooldown permits
- **THEN** AIService SHALL report the event with track, person bbox, confidence, and source
- **AND** unmatched helmet detections SHALL NOT enter persistent cache or trigger events

### Requirement: Fall detection

AIService SHALL evaluate tracked temporal evidence before emitting a fall event.

#### Scenario: Confirm fall over time

- **GIVEN** one track has continuous bbox and optional pose history
- **WHEN** configured posture and duration thresholds indicate a fall
- **THEN** AIService SHALL output a high-severity fall event

### Requirement: Warning-zone detection

AIService SHALL evaluate enabled camera polygons against tracked person foot points.

#### Scenario: Detect intrusion or dwell

- **GIVEN** enabled camera polygons and person foot points are available
- **WHEN** a tracked person enters or remains in a zone
- **THEN** AIService SHALL produce the corresponding region event with zone and track context

### Requirement: Running detection

AIService SHALL support sustained pixel-speed evaluation for tracked people.

#### Scenario: Detect sustained speed

- **GIVEN** a track has timestamped center or foot points
- **WHEN** pixel speed exceeds the configured threshold for the confirmation window
- **THEN** AIService MAY output a running event

### Requirement: Detection work shall not create frame backlog

The stream pipeline SHALL prefer the latest frame and SHALL bound pending work.

#### Scenario: Slow optional detector

- **GIVEN** an optional detector takes longer than the source frame interval
- **WHEN** new frames arrive
- **THEN** processing SHALL use the latest available frame rather than queue every frame
- **AND** disabled detectors SHALL not execute or generate events
