# Person Detection

## Requirement: Reserve Person Detection Pipeline

The system SHALL provide a person detection module for real-time human detection and processed video output.

### Scenario: Inspect detector placeholder

- GIVEN the AI service receives a frame from a video stream
- WHEN person detection runs
- THEN the module SHALL output `PERSON_DETECTION` results with `bbox`, `trackId`, and `confidence`
- AND the AI service SHALL be able to draw those results onto the processed video stream
