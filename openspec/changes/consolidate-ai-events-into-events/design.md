# Design: Event model migration for AI report persistence

## Current State

`POST /api/ai-results/report/` currently receives AIService frame results and persists them through `apps.ai_results.AIEvent`. `Alert` is also owned by `ai_results` and points to `AIEvent`.

This made the P0 AIService chain testable quickly, but it leaves the formal `events` app as a placeholder while the temporary model already behaves like an event table.

## Target State

`apps.events.Event` becomes the canonical event record for AI detections. `ai_results` remains the ingestion boundary for AIService HTTP reports.

The flow becomes:

1. AIService posts the existing payload to `/api/ai-results/report/`.
2. Backend validates the existing serializer.
3. Backend creates one `events.Event` per accepted result.
4. Backend double-writes one `AIEvent` per accepted result during transition.
5. Backend creates `Alert` only for alert-class result types.
6. Response keeps the existing compatibility fields.

## Event Fields

- `camera`: optional FK to `Camera`
- `camera_identifier`: original `cameraId` or camera code from the report
- `event_type`: AI result type, for example `PERSON_DETECTION`
- `source`: currently fixed to `ai_service`
- `severity`: `info`, `low`, `medium`, or `high`
- `status`: lifecycle status, initially `new`
- `occurred_at`: AI report timestamp
- `frame_id`: source frame id
- `track_id`: detected track id when present
- `bbox`: detected bounding box
- `confidence`: score, similarity, or confidence when present
- `snapshot_path`: snapshot path/url when present
- `payload`: raw AI result object
- `created_at`, `updated_at`: persistence timestamps

## Compatibility

`AIEvent` is not deleted in this change. The report endpoint double-writes it so existing migrations, admin usage, tests, or downstream code that still reads `AIEvent` are not broken.

`Alert.event` currently points to `AIEvent`, so this change keeps that relation and adds `Alert.system_event` pointing to the formal `events.Event`. A later cleanup can rename fields or migrate old alert data after the event center is stable.

## Risk Controls

- No AIService request payload changes.
- No video-streaming changes.
- No frontend monitor changes.
- No data migration that deletes or rewrites existing `AIEvent` rows.
- The new `Event` model is additive.
