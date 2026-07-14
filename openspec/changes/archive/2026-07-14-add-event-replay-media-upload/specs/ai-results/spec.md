## ADDED Requirements

### Requirement: Upload event replay media

After the backend accepts an actionable AI event, AIService SHALL upload completed replay media for that event when local media files are available.

#### Scenario: Backend accepts event media upload

- **GIVEN** a formal `Event` exists
- **WHEN** AIService uploads multipart media to `POST /api/events/{event_id}/media/`
- **THEN** the backend SHALL save provided files under runtime media storage
- **AND** SHALL update `Event.payload.media` with browser-accessible URLs for saved files
- **AND** SHALL return the updated media metadata

#### Scenario: Upload remains non-blocking

- **GIVEN** AIService is processing a live stream
- **WHEN** event replay media is being encoded or uploaded
- **THEN** encoding and upload SHALL NOT run on the real-time frame processing path
- **AND** upload failures SHALL NOT mark the original event report as failed
- **AND** media tasks SHALL use a bounded queue so repeated events cannot grow memory without limit

#### Scenario: Runtime media is not committed

- **GIVEN** AIService or backend creates keyframes, clips, manifests, or fallback frame sequences
- **WHEN** repository changes are inspected
- **THEN** generated media artifacts SHALL remain ignored by Git
