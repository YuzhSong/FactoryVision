# Change: Consolidate AI events into the formal Events module

## Why

`AIEvent` was introduced as a fast P0 persistence target so the AIService local chain could report detection results without waiting for a full event center design. That table now overlaps with the planned `events` app: it stores camera, event type, occurrence time, bbox, confidence, snapshot, and raw payload.

Keeping `AIEvent` as the only persisted event path would make future alert center, audit, playback, and event search features depend on a temporary ai-results-owned model. The safer direction is to establish `apps.events.Event` as the formal event center record and let the existing AI report endpoint write into it.

## What Changes

- Add a formal `Event` model in `backend/apps/events/models.py`.
- Keep `AIEvent` and `apps.ai_results` in place for compatibility.
- Update `POST /api/ai-results/report/` so every accepted result creates one `events.Event`.
- Double-write `AIEvent` during the transition so existing code and migrations are not broken.
- Continue creating `Alert` for alert-class event types.
- Link `Alert` to the formal `Event` through a new compatibility field while retaining the old `AIEvent` relation.
- Keep the AIService request payload and endpoint URL unchanged.

## Affected Specs

- `ai-results`
- `event-alert`

## Non-Goals

- Do not delete `AIEvent`.
- Do not remove the `ai_results` app.
- Do not change the AIService payload shape.
- Do not change video streaming, detection, or frontend monitor playback logic.
- Do not add a message queue or async event pipeline.
- Do not redesign the full alert center UI.

## Acceptance

- `POST /api/ai-results/report/` accepts the existing AIService payload.
- A `PERSON_DETECTION` result creates one `events.Event` and no alert.
- An alert-class result such as `ZONE_WARNING` or `HELMET_WARNING` creates one `events.Event` and one `Alert`.
- The response remains compatible with `acceptedResults`, `eventIds`, `alertIds`, `cameraId`, and `frameId`.
- `eventIds` refers to formal `events.Event` ids after this change.
- Transitional `AIEvent` rows may still be written and documented.
