## MODIFIED Requirements

### Requirement: AI events shall be deduplicated by event policy

Actionable AI results SHALL be persisted once per relevant event window so continuous observations do not flood alerts.

#### Scenario: Region intrusion uses medium severity and cooldown

- **GIVEN** AIService reports `region_intrusion` for the same camera, region, track, and event type
- **WHEN** a previous intrusion event exists within the intrusion cooldown window
- **THEN** the duplicate SHALL be rejected
- **AND** accepted intrusion events SHALL default to medium severity

#### Scenario: Region dwell uses high severity and longer cooldown

- **GIVEN** AIService reports `region_dwell` for the same camera, region, track, and event type
- **WHEN** a previous dwell event exists within the dwell cooldown window
- **THEN** the duplicate SHALL be rejected
- **AND** accepted dwell events SHALL default to high severity

### Requirement: Event replay clips shall be browser playable

AIService SHALL generate short replay clips in a browser-playable format when ffmpeg is available.

#### Scenario: H.264 MP4 clip is generated

- **GIVEN** event media recording is enabled and ffmpeg is available
- **WHEN** a short event clip is finalized
- **THEN** the clip SHALL be encoded as H.264 MP4 with yuv420p pixels
- **AND** the file SHALL be optimized for browser playback
- **AND** failures SHALL fall back to keyframe/manifest evidence without blocking event reporting
