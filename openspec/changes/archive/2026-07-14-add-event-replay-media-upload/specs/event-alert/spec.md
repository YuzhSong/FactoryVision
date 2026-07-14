## MODIFIED Requirements

### Requirement: Alert detail shall expose replay-ready event evidence

`GET /api/alerts/{id}/detail/` SHALL return alert metadata, linked event metadata, and replay evidence suitable for a detail drawer.

#### Scenario: Return uploaded media URLs

- **GIVEN** an event has uploaded replay media saved in `Event.payload.media`
- **WHEN** the frontend requests `GET /api/alerts/{id}/detail/`
- **THEN** the response SHALL include `replay.media.keyframeUrl` when a keyframe was uploaded
- **AND** the response SHALL include `replay.media.clipUrl` when a short clip was uploaded
- **AND** missing media URLs SHALL NOT prevent the detail response from returning trajectory and log data

#### Scenario: Display uploaded replay media

- **GIVEN** the alert detail response contains `replay.media.keyframeUrl` or `replay.media.clipUrl`
- **WHEN** the detail drawer is open
- **THEN** the frontend SHALL display the keyframe image when available
- **AND** SHALL display a playable video element when `clipUrl` is available
- **AND** SHALL keep the trajectory preview visible even when uploaded media is unavailable
