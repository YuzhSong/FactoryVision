## ADDED Requirements

### Requirement: Report replay trajectory evidence

The AI service SHALL include bounded trajectory evidence for actionable events when track history is available.

#### Scenario: Actionable event includes trajectory

- **GIVEN** the AI service has recent lightweight track history for an event `trackId`
- **WHEN** it reports an actionable event to `POST /api/ai-results/report/`
- **THEN** the event result SHALL include a `trajectory` array with recent points
- **AND** each point SHALL contain `timestamp`, `center`, `bbox`, and optional `speed`, `frameIndex`, or `keypoints`
- **AND** the trajectory SHALL be bounded by configured history limits and SHALL NOT include raw frame image data

#### Scenario: Backend persists replay evidence

- **GIVEN** the backend accepts an actionable AI result containing `trajectory`, region context, and media metadata
- **WHEN** it creates the formal `Event`
- **THEN** the backend SHALL preserve that replay evidence in `Event.payload`
- **AND** generated media file paths SHALL remain runtime artifacts and SHALL NOT be committed to the repository

### Requirement: Event media remains non-blocking

Event media generation SHALL NOT block real-time AI processing or event reporting.

#### Scenario: First phase without video upload

- **GIVEN** an actionable event is detected
- **WHEN** replay detail is generated in this change
- **THEN** key JSON evidence MAY be reported immediately
- **AND** short video upload MAY remain unavailable
- **AND** lack of `clipUrl` SHALL NOT prevent event creation or alert detail display
