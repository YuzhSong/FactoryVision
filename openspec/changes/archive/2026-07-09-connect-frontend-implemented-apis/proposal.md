# Change: Connect frontend pages to implemented backend APIs

## Why

Several backend APIs are now implemented, but related frontend pages still use static placeholder data. This causes the UI to diverge from real backend state and prevents end-to-end verification.

## What Changes

- Connect Employees page to `employeesApi.list()` and `employeesApi.create()`.
- Connect Cameras page to `camerasApi.list()`.
- Connect Zones page to `zonesApi.list()`.
- Keep planned or missing write operations disabled or explicitly labeled as planned.
- Preserve placeholder fallback only when the API is unavailable or returns no data.

## Affected Specs

- employee-management
- camera-management
- warning-zone

## Acceptance

- Employees table loads data from `GET /api/employees/list/`.
- Employee filters send `keyword`, `department`, and `status`.
- Creating an employee refreshes the employee table.
- Cameras table loads data from `GET /api/cameras/list/`.
- Zones table loads data from `GET /api/zones/list/` and can filter by selected camera.
- Frontend build passes.
