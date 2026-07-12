# Change: Enhance frontend warning zone editor

## Why

The zone configuration page currently shows only a polygon placeholder and does not submit the implemented backend zone creation API. Users need to draw a danger area on the selected camera view and save it through the backend.

## What Changes

- Replace the static zone placeholder with an interactive polygon editor on the monitor area.
- Allow users to click to add points, drag existing points, undo the last point, and clear the draft.
- Add zone name, type, enabled, and description inputs that match the backend zone creation contract.
- Submit valid polygons to `POST /api/zones/` and refresh the zone list after creation.

## Affected Specs

- `warning-zone`

## Non-Goals

- Do not add or change database models or migrations.
- Do not change the zone list API contract.

## Acceptance

- The page lets users draft a polygon with at least three points on the selected camera area.
- Points are stored as normalized coordinates so they can be mapped to different video sizes.
- Saving calls the backend zone creation endpoint only when a camera, zone name, and at least three points are present.
