from datetime import datetime, timezone
import math


class ZoneDetector:
    """Track region entry and dwell state for person foot points in polygon zones."""

    def __init__(self, zones=None, min_stay_seconds=10.0, state_ttl_seconds=30.0):
        self.zones = list(zones or [])
        self.min_stay_seconds = max(0.0, float(min_stay_seconds or 0))
        self.state_ttl_seconds = max(1.0, float(state_ttl_seconds or 1))
        self._states = {}

    def set_zones(self, zones):
        self.zones = list(zones or [])

    def reset(self):
        self._states.clear()

    def detect_events(self, camera_id, detections, timestamp=None, frame_shape=None):
        """Return each region intrusion/dwell event at most once per continuous stay."""
        timestamp = timestamp or _now_iso()
        now = _timestamp_seconds(timestamp)
        self._purge_expired(now)
        events = []
        for detection in detections or []:
            track_id = detection.get("trackId")
            foot_point = self._get_foot_point(detection)
            if track_id in (None, ""):
                continue
            confidence = detection.get("confidence")
            hit_points = self._get_hit_points(detection)
            if not hit_points:
                continue

            for zone in self.zones:
                if not isinstance(zone, dict) or not zone.get("enabled", True):
                    continue
                region_id = self._zone_id(zone)
                points = self._get_zone_points(zone, frame_shape)
                if region_id in (None, "") or len(points) < 3:
                    continue
                key = self._state_key(camera_id, region_id, track_id)
                hit_point = next((point for point in hit_points if self._point_in_polygon(point, points)), None)
                inside = hit_point is not None
                if not inside:
                    continue

                state = self._states.get(key)
                if state is None:
                    state = {
                        "enteredAt": timestamp,
                        "enteredSeconds": now,
                        "lastSeenAt": timestamp,
                        "lastSeenSeconds": now,
                        "intrusionEmitted": False,
                        "dwellEmitted": False,
                    }
                    self._states[key] = state
                else:
                    state["lastSeenAt"] = timestamp
                    state["lastSeenSeconds"] = now

                duration = max(0.0, now - state["enteredSeconds"])
                if self._is_restricted(zone) and not state["intrusionEmitted"]:
                    events.append(self._event("region_intrusion", camera_id, track_id, zone, state, duration, confidence, hit_point))
                    state["intrusionEmitted"] = True
                if duration >= self._min_stay_seconds(zone) and not state["dwellEmitted"]:
                    events.append(self._event("region_dwell", camera_id, track_id, zone, state, duration, confidence, hit_point))
                    state["dwellEmitted"] = True

        # Keep a briefly missing track until TTL expiry; detector tracking can drop frames temporarily.
        return events

    def state_count(self):
        return len(self._states)

    def _event(self, event_type, camera_id, track_id, zone, state, duration, confidence, foot_point):
        region_id = self._zone_id(zone)
        return {
            "type": "ZONE_WARNING",
            "eventType": event_type,
            "cameraId": camera_id,
            "trackId": track_id,
            "regionId": region_id,
            "regionName": zone.get("name", zone.get("zoneName")),
            "regionType": zone.get("type", "restricted"),
            # zone aliases retain compatibility with current backend alert descriptions.
            "zoneId": region_id,
            "zoneName": zone.get("name", zone.get("zoneName")),
            "enteredAt": state["enteredAt"],
            "durationSeconds": round(duration, 2),
            "timestamp": state["lastSeenAt"],
            "confidence": round(float(confidence or 0), 4),
            "footPoint": {"x": round(foot_point[0], 2), "y": round(foot_point[1], 2)},
            "level": "high" if event_type == "region_intrusion" else "medium",
        }

    def _state_key(self, camera_id, region_id, track_id):
        return str(camera_id), str(region_id), str(track_id)

    def _purge_expired(self, now):
        self._states = {
            key: state for key, state in self._states.items()
            if now - state.get("lastSeenSeconds", now) <= self.state_ttl_seconds
        }

    def _is_restricted(self, zone):
        return str(zone.get("type", "restricted")).lower() in {"restricted", "danger"}

    def _min_stay_seconds(self, zone):
        value = zone.get("minStaySeconds", zone.get("min_stay_seconds", self.min_stay_seconds))
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return self.min_stay_seconds

    def _zone_id(self, zone):
        return zone.get("id", zone.get("zoneId", zone.get("regionId")))

    def _get_foot_point(self, detection):
        foot_point = detection.get("footPoint")
        if isinstance(foot_point, dict):
            return float(foot_point.get("x", 0)), float(foot_point.get("y", 0))
        bbox = detection.get("bbox")
        if isinstance(bbox, dict):
            return (float(bbox.get("x1", 0)) + float(bbox.get("x2", 0))) / 2, float(bbox.get("y2", 0))
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return (float(bbox[0]) + float(bbox[2])) / 2, float(bbox[3])
        return None

    def _get_hit_points(self, detection):
        points = []
        foot_point = self._get_foot_point(detection)
        if foot_point is not None:
            points.append(foot_point)
        bbox = detection.get("bbox")
        if isinstance(bbox, dict):
            x1 = float(bbox.get("x1", 0))
            y1 = float(bbox.get("y1", 0))
            x2 = float(bbox.get("x2", 0))
            y2 = float(bbox.get("y2", 0))
        elif isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            x1, y1, x2, y2 = map(float, bbox)
        else:
            return points
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        points.extend([
            (center_x, center_y),
            (center_x, y1 + (y2 - y1) * 0.33),
            (center_x, y1 + (y2 - y1) * 0.66),
        ])
        return points

    def _get_zone_points(self, zone, frame_shape):
        points = zone.get("points") or zone.get("polygonPoints") or []
        normalized = []
        for point in points:
            if isinstance(point, dict):
                normalized.append((float(point.get("x", 0)), float(point.get("y", 0))))
            elif isinstance(point, (list, tuple)) and len(point) == 2:
                normalized.append((float(point[0]), float(point[1])))
        if frame_shape and normalized and _uses_normalized_coordinates(normalized):
            height, width = frame_shape[:2]
            scale = 100.0 if _uses_percentage_coordinates(normalized) else 1.0
            return [(x * width / scale, y * height / scale) for x, y in normalized]
        return normalized

    def _point_in_polygon(self, point, polygon):
        if any(self._distance_to_segment(point, start, end) <= 1e-6 for start, end in zip(polygon, polygon[1:] + polygon[:1])):
            return True
        x, y = point
        inside = False
        previous_x, previous_y = polygon[-1]
        for current_x, current_y in polygon:
            if (current_y > y) != (previous_y > y):
                intersect_x = (previous_x - current_x) * (y - current_y) / (previous_y - current_y) + current_x
                if x < intersect_x:
                    inside = not inside
            previous_x, previous_y = current_x, current_y
        return inside

    def _distance_to_segment(self, point, start, end):
        px, py = point
        sx, sy = start
        ex, ey = end
        dx, dy = ex - sx, ey - sy
        if dx == 0 and dy == 0:
            return math.dist(point, start)
        ratio = max(0, min(1, ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)))
        return math.dist(point, (sx + ratio * dx, sy + ratio * dy))


def _timestamp_seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return datetime.now(timezone.utc).timestamp()


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def _uses_normalized_coordinates(points):
    """Support current 0..1 points and legacy 0..100 percentage points."""
    return all(0 <= x <= 100 and 0 <= y <= 100 for x, y in points)


def _uses_percentage_coordinates(points):
    return any(x > 1 or y > 1 for x, y in points)
