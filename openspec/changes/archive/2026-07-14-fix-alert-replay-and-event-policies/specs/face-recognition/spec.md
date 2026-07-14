## MODIFIED Requirements

### Requirement: Face library cache shall reflect employee deletion

AIService SHALL stop recognizing employees whose face records were removed from the backend face library.

#### Scenario: Employee deletion clears AIService face identity cache

- **GIVEN** an employee is deleted or the face library is reloaded
- **WHEN** AIService applies the face library update
- **THEN** matching face records for the removed employee SHALL be removed
- **AND** short-lived track identity caches SHALL be invalidated so stale labels are not reused
