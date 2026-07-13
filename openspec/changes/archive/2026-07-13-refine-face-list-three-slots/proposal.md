# Change: Three-slot face list response

## Why

Face list returned flat array. Frontend needs predictable 3-slot format (front/left/right, null if missing).

## What Changes

- `GET /api/employees/{id}/faces/` returns `{front: {...}|null, left: {...}|null, right: {...}|null}`
