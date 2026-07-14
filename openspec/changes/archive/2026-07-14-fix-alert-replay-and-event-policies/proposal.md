# Change: Fix alert replay and event notification policies

## Why

Alert evidence is present but the replay drawer still shows a misleading trajectory sketch, generated clips use an MP4 codec that many browsers cannot play, region events can repeat too aggressively, and medium-risk alerts should not escalate in DingTalk. Employee face deletion also needs stronger AIService cache invalidation so removed employees are not recognized from short-lived local caches.

## What Changes

- Simplify the alert detail drawer to show uploaded keyframes, playable short clips, media paths, and the raw event log without the standalone trajectory sketch.
- Encode event replay clips as browser-playable H.264 MP4 when ffmpeg is available, while keeping clip failure non-fatal.
- Keep helmet detection on the current open-source helmet model and preserve diagnostics for checking detection, person matching, and warning generation.
- Invalidate AIService face identity caches when the face library is reloaded, upserted, or deleted.
- Change region severity policy so intrusion is medium risk and dwell is high risk, with time-based cooldowns for both.
- Send DingTalk escalation only for high-risk alerts; medium-risk alerts receive the initial responsible-person notification only.

## Safety

- Runtime event media remains ignored and SHALL NOT be committed.
- Event media encoding/upload failures SHALL NOT block live detection or event reporting.
- Face cache invalidation SHALL be safe even when AIService is unreachable from the cloud backend.
