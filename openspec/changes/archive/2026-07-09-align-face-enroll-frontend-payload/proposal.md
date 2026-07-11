# Change: Align frontend face enrollment payload

## Why

The backend face enrollment endpoint has been implemented and now requires three face images in a `faces` array. The frontend still submits the previous compatibility payload, so submitted photos cannot be accepted by the backend serializer.

## What Changes

- Update the frontend face enrollment request payload to match `POST /api/face/enroll/`.
- Submit exactly three images with `faceType` values `front`, `left`, and `right`.
- Keep the existing three-photo UI and camera capture flow.
- Surface backend validation errors clearly when enrollment fails.

## Affected Specs

- face-recognition
- employee-management

## Acceptance

- Frontend submits `employeeId` and `faces`.
- Each `faces` item contains `imageBase64` and `faceType`.
- Missing any of front/left/right photos blocks submission before the API call.
- `npm run build` passes after the change.
