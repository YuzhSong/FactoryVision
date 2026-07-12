## ADDED Requirements

### Requirement: Dashboard summary API

The system SHALL provide a database-backed dashboard summary for operational monitoring.

#### Scenario: Return dashboard summary

- GIVEN Camera, Employee, Event, or Alert records may exist
- WHEN `GET /api/dashboard/summary/` is called
- THEN the response SHALL include cameraCount, onlineCameraCount, employeeCount, todayEventCount, todayAlertCount, pendingAlertCount, recentAlerts, and eventTrend
- AND recentAlerts SHALL be read from Alert records linked to formal Event records
- AND eventTrend SHALL aggregate today's Event records by `occurred_at` hour
- AND no returned value SHALL be hardcoded or depend on placeholder data
