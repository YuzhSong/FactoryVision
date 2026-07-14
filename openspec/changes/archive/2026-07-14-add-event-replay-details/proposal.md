# Change: Add event replay details

## Why

Operators need evidence after an alert is generated, not only a row in the alert list. The current alert center can list and handle alerts, but "查看" only opens a basic drawer with summary fields. The AI service already keeps lightweight track history and has an event media recorder skeleton, but replay evidence is not persisted in a frontend-friendly way.

## What Changes

- Add a backend alert detail endpoint that returns alert, linked event, replay metadata, and raw payload evidence.
- Persist lightweight trajectory data from the AI service into the existing `Event.payload` when a report result contains track history.
- Surface replay evidence in the frontend alert detail view:
  - full alert log fields;
  - key event data;
  - trajectory points drawn over a normalized preview canvas;
  - region/zone context when present;
  - media placeholders for keyframe and future clip URLs.
- Keep generated frames and video clips as runtime media only; they SHALL NOT be committed to Git.

## Scope

### In scope for this change

- First-phase replay details: JSON trajectory, region context, bbox, confidence, and alert/event detail UI.
- Backend serializers and API routes for alert detail.
- AI service report enrichment with bounded trajectory points.
- Tests for backend persistence and frontend build.

### Out of scope for this change

- Continuous full video recording.
- Synchronous MP4 encoding or upload from the AI processing thread.
- Public cloud media upload for `clip.mp4`.
- Long-term media retention and cleanup policies.

## Affected Specs

- `event-alert`
- `ai-results`

