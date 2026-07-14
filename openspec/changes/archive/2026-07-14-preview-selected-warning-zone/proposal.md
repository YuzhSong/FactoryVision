# Change: Preview selected warning zone on editor

## Why

The warning zone page lists saved zones and provides a drawing editor, but selecting a saved zone does not show its polygon on the editor. Users need a quick way to inspect existing zone geometry before drawing a new zone.

## What Changes

- Allow users to click a saved zone row in the zone table.
- Render the selected saved zone polygon on the editor using its normalized points.
- Highlight the selected row so the preview target is clear.
- Clear the saved-zone preview automatically when the user starts editing a new draft on the canvas.

## Affected Specs

- `warning-zone`

## Non-Goals

- Do not add backend APIs.
- Do not edit existing saved zones.
- Do not change the stored `points` coordinate contract.

## Acceptance

- Clicking a zone row previews its polygon in the upper editor.
- Starting a draft by clicking the editor removes the selected saved-zone preview.
- Creating and saving a new zone still uses the existing `POST /api/zones/` flow.
