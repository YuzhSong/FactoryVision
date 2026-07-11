from datetime import datetime, timezone


class EmployeePresenceDetector:
    """Maintain employee present/absent state from recognized face results."""

    def __init__(self, absence_timeout_seconds: float = 60.0, min_similarity: float = 0.0):
        """Initialize leave/return thresholds."""
        self.absence_timeout_seconds = float(absence_timeout_seconds)
        self.min_similarity = float(min_similarity)
        self.states = {}

    def detect(self, face_results, camera_id=None, frame_id=None, timestamp=None):
        """Update employee states and return leave/return events."""
        timestamp = timestamp or datetime.now(timezone.utc).astimezone().isoformat()
        now_seconds = _parse_timestamp(timestamp)
        if now_seconds is None:
            now_seconds = datetime.now(timezone.utc).timestamp()

        events = []
        seen_keys = set()
        for face_result in face_results or []:
            if not self._is_recognized_employee(face_result):
                continue

            key = self._employee_key(face_result)
            if not key:
                continue

            seen_keys.add(key)
            events.extend(self._mark_present(key, face_result, now_seconds, timestamp, camera_id, frame_id))

        events.extend(self._mark_absent_for_stale_employees(seen_keys, now_seconds, timestamp, camera_id, frame_id))
        return events

    def status(self):
        """Return a lightweight snapshot of employee presence state."""
        employees = [self._public_state(state) for state in self.states.values()]
        return {
            "absenceTimeoutSeconds": self.absence_timeout_seconds,
            "employeeCount": len(self.states),
            "presentCount": sum(1 for employee in employees if employee.get("status") == "present"),
            "absentCount": sum(1 for employee in employees if employee.get("status") == "absent"),
            "employees": employees,
        }

    def reset(self):
        """Clear all employee presence state."""
        self.states = {}

    def _mark_present(self, key, face_result, now_seconds, timestamp, camera_id, frame_id):
        state = self.states.get(key)
        previous_status = state.get("status") if state else None
        previous_leave_started_at = state.get("leaveStartedAt") if state else None
        leave_duration = 0.0
        if state and previous_status == "absent" and state.get("leaveStartSeconds") is not None:
            leave_duration = max(0.0, now_seconds - state["leaveStartSeconds"])

        updated = {
            **(state or {}),
            "key": key,
            "employeeId": face_result.get("employeeId"),
            "employeeNo": face_result.get("employeeNo"),
            "name": face_result.get("name"),
            "status": "present",
            "lastSeen": timestamp,
            "lastSeenSeconds": now_seconds,
            "lastSimilarity": face_result.get("similarity"),
            "leaveStartedAt": None,
            "leaveStartSeconds": None,
            "leaveDurationSeconds": 0.0,
        }
        self.states[key] = updated

        if previous_status != "absent":
            return []

        return [
            self._event(
                event_type="RETURN",
                state=updated,
                camera_id=camera_id,
                frame_id=frame_id,
                timestamp=timestamp,
                leave_duration_seconds=leave_duration,
                leave_started_at=previous_leave_started_at,
            )
        ]

    def _mark_absent_for_stale_employees(self, seen_keys, now_seconds, timestamp, camera_id, frame_id):
        events = []
        for key, state in list(self.states.items()):
            if key in seen_keys or state.get("status") == "absent":
                continue

            last_seen_seconds = state.get("lastSeenSeconds")
            if last_seen_seconds is None:
                continue

            missing_seconds = now_seconds - last_seen_seconds
            if missing_seconds < self.absence_timeout_seconds:
                continue

            state["status"] = "absent"
            state["leaveStartedAt"] = state.get("lastSeen")
            state["leaveStartSeconds"] = last_seen_seconds
            state["leaveDurationSeconds"] = round(max(0.0, missing_seconds), 2)
            events.append(
                self._event(
                    event_type="LEAVE",
                    state=state,
                    camera_id=camera_id,
                    frame_id=frame_id,
                    timestamp=timestamp,
                    leave_duration_seconds=missing_seconds,
                    leave_started_at=state.get("leaveStartedAt"),
                )
            )

        return events

    def _event(
        self,
        event_type,
        state,
        camera_id,
        frame_id,
        timestamp,
        leave_duration_seconds,
        leave_started_at=None,
    ):
        status = "present" if event_type == "RETURN" else "absent"
        return {
            "type": "EMPLOYEE_PRESENCE_EVENT",
            "eventType": event_type,
            "employeeId": state.get("employeeId"),
            "employeeNo": state.get("employeeNo"),
            "name": state.get("name"),
            "status": status,
            "cameraId": camera_id,
            "frameId": frame_id,
            "timestamp": timestamp,
            "lastSeen": state.get("lastSeen"),
            "leaveStartedAt": leave_started_at if leave_started_at is not None else state.get("leaveStartedAt"),
            "leaveDurationSeconds": round(max(0.0, leave_duration_seconds), 2),
            "level": "medium" if event_type == "LEAVE" else "low",
        }

    def _public_state(self, state):
        return {
            "employeeId": state.get("employeeId"),
            "employeeNo": state.get("employeeNo"),
            "name": state.get("name"),
            "status": state.get("status"),
            "lastSeen": state.get("lastSeen"),
            "leaveStartedAt": state.get("leaveStartedAt"),
            "leaveDurationSeconds": state.get("leaveDurationSeconds", 0.0),
            "lastSimilarity": state.get("lastSimilarity"),
        }

    def _is_recognized_employee(self, face_result):
        if face_result.get("type") != "FACE_RESULT":
            return False
        if face_result.get("matched") is not True:
            return False
        if self._employee_key(face_result) is None:
            return False

        similarity = face_result.get("similarity")
        if similarity is None:
            return True
        try:
            return float(similarity) >= self.min_similarity
        except (TypeError, ValueError):
            return False

    def _employee_key(self, face_result):
        employee_id = face_result.get("employeeId")
        if employee_id not in (None, ""):
            return f"id:{employee_id}"

        employee_no = face_result.get("employeeNo")
        if employee_no not in (None, ""):
            return f"no:{employee_no}"

        return None


def _parse_timestamp(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return None
