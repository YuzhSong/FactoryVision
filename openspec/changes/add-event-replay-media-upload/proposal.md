# Change: Add event replay media upload

## Why

The first replay phase shows event logs, trajectory, region context, and media placeholders. Operators still need a short, browser-accessible clip for intuitive evidence review. Local Windows paths from AIService are not reachable by the cloud backend or frontend.

## What Changes

- Add a backend endpoint for AIService to upload event media files after an event is accepted.
- Store uploaded keyframes, clips, and manifests under runtime media storage and update the linked `Event.payload.media` fields with public media URLs.
- Let AIService map accepted backend event IDs to local recorder media bundles, then upload completed media from a bounded background path.
- Keep clip upload failures non-fatal for real-time detection and event reporting.
- Render uploaded keyframes and playable short videos in the alert detail drawer when URLs are available.

## Scope

In scope:
- `POST /api/events/{event_id}/media/`
- multipart upload for `keyframe`, `clip`, and `manifest`
- bounded local recorder finalization queue
- AIService background upload after backend event creation
- frontend keyframe/video display

Out of scope:
- continuous full-time recording
- object storage/CDN integration
- permissioned signed URLs
- long-term media retention cleanup

## Safety

- Generated clips and frames remain runtime artifacts only and SHALL NOT be committed to Git.
- Upload and clip generation failures SHALL NOT block AI inference, event reporting, or live stream output.
