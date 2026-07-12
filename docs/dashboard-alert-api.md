# Dashboard and Alert APIs

All responses use the common `{code, message, data, requestId}` envelope.

## List Alerts

`GET /api/alerts/list/`

Optional query parameters:

- `page`: positive page number, default `1`
- `pageSize`: page size from `1` to `100`, default `20`
- `severity`: Alert severity (`high`, `medium`, and so on)
- `status`: Alert status (`pending`, `processing`, `closed`)
- `cameraId`: positive camera id

`data` has this shape:

```json
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "title": "Zone Warning",
      "eventType": "ZONE_WARNING",
      "severity": "high",
      "status": "pending",
      "cameraId": 1,
      "cameraName": "Workshop A",
      "occurredAt": "2026-07-10T10:00:00+08:00",
      "description": "trackId=t-1"
    }
  ]
}
```

Data comes from `Alert`, with camera display data from `Alert.camera` and the formal event relation `Alert.event -> Event`.

## Handle Alert

`POST /api/alerts/{id}/handle/`

Request body:

```json
{"status": "processing"}
```

The endpoint updates only `Alert.status`. The current Alert model has no handler or handling-time fields, so neither is fabricated.

## Dashboard Summary

`GET /api/dashboard/summary/`

`data` includes:

- `cameraCount`: all Camera records
- `onlineCameraCount`: Camera records with `status=online`
- `employeeCount`: all Employee records
- `todayEventCount`: Event records whose `occurred_at` is today in the configured local timezone
- `todayAlertCount`: Alert records whose `occurred_at` is today
- `pendingAlertCount`: Alert records with `status=pending`
- `recentAlerts`: up to five newest alerts using the alert item structure above
- `eventTrend`: today's Event records grouped by local `occurred_at` hour, each item is `{hour, count}`

All dashboard values are read from Camera, Employee, Event, and Alert. This endpoint intentionally has no attendance field because the project does not yet have a formal attendance data source.
