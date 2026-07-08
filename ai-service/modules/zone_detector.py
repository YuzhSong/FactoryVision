from datetime import datetime, timezone
import math


class ZoneDetector:
    """Detect zone intrusion from person foot points and polygon zones."""

    def __init__(self, zones=None, min_stay_seconds: float = 10.0, state_ttl_seconds: float = 30.0):
        """Initialize zone detector with optional zones."""
        self.zones = []
        self.min_stay_seconds = max(0.0, float(min_stay_seconds or 0))
        self.state_ttl_seconds = max(1.0, float(state_ttl_seconds or 1))
        self._states = {}
        if zones:
            self.set_zones(zones)

    def set_zones(self, zones):
        """Replace active warning zone definitions."""
        self.zones = zones or []
        active_zone_ids = {str(self._zone_id(zone)) for zone in self.zones}
        self._states = {
            key: state
            for key, state in self._states.items()
            if key[1] in active_zone_ids
        }

    def detect_intrusion(self, detections, timestamp=None):
        """Return ZONE_WARNING results for detections inside or near zones."""
        timestamp = timestamp or _now_iso()
        now_seconds = _timestamp_seconds(timestamp)
        self._purge_expired(now_seconds)

        warnings = []
        for detection in detections or []:
            track_id = detection.get("trackId")
            foot_point = self._get_foot_point(detection)
            if foot_point is None or track_id in (None, ""):
                continue

            for zone in self.zones:
                points = self._get_zone_points(zone)
                if len(points) < 3:
                    continue

                inside = self._point_in_polygon(foot_point, points)
                distance = 0 if inside else self._distance_to_polygon(foot_point, points)
                safe_distance = zone.get("safeDistance", zone.get("safe_distance", 0)) or 0

                if inside or distance <= safe_distance:
                    state = self._update_state(
                        track_id=track_id,
                        zone=zone,
                        now_seconds=now_seconds,
                        timestamp=timestamp,
                    )
                    stay_seconds = now_seconds - state["firstRiskSeconds"]
                    min_stay_seconds = self._min_stay_seconds(zone)
                    if stay_seconds >= min_stay_seconds:
                        warnings.append(
                            {
                                "type": "ZONE_WARNING",
                                "trackId": track_id,
                                "zoneId": self._zone_id(zone),
                                "zoneName": zone.get("name", zone.get("zoneName")),
                                "footPoint": {"x": foot_point[0], "y": foot_point[1]},
                                "inside": inside,
                                "distance": round(distance, 2),
                                "safeDistance": safe_distance,
                                "staySeconds": round(stay_seconds, 2),
                                "minStaySeconds": min_stay_seconds,
                                "firstRiskAt": state["firstRiskAt"],
                                "lastRiskAt": timestamp,
                                "level": self._get_level(inside),
                            }
                        )
                else:
                    self._clear_state(track_id, zone)

        return warnings

    def _get_foot_point(self, detection):
        """Extract foot point from detection, falling back to bbox bottom center."""
        foot_point = detection.get("footPoint")
        if isinstance(foot_point, dict):
            return (foot_point.get("x", 0), foot_point.get("y", 0))
        if isinstance(foot_point, (list, tuple)) and len(foot_point) == 2:
            return (foot_point[0], foot_point[1])

        bbox = detection.get("bbox")
        if isinstance(bbox, dict):
            return ((bbox.get("x1", 0) + bbox.get("x2", 0)) / 2, bbox.get("y2", 0))
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            x1, _y1, x2, y2 = bbox
            return ((x1 + x2) / 2, y2)

        return None

    def _get_zone_points(self, zone):
        """Normalize zone polygon points to tuple coordinates."""
        points = zone.get("points") or zone.get("polygonPoints") or []
        normalized_points = []
        for point in points:
            if isinstance(point, dict):
                normalized_points.append((point.get("x", 0), point.get("y", 0)))
            elif isinstance(point, (list, tuple)) and len(point) == 2:
                normalized_points.append((point[0], point[1]))
        return normalized_points

    def _point_in_polygon(self, point, polygon):
        """Return whether point lies inside polygon using ray casting."""
        x, y = point
        inside = False
        previous_x, previous_y = polygon[-1]

        for current_x, current_y in polygon:
            intersects = (current_y > y) != (previous_y > y)
            if intersects:
                slope_x = (previous_x - current_x) * (y - current_y) / ((previous_y - current_y) or 1e-9) + current_x
                if x < slope_x:
                    inside = not inside
            previous_x, previous_y = current_x, current_y

        return inside

    def _distance_to_polygon(self, point, polygon):
        """Calculate shortest distance from point to polygon edges."""
        distances = []
        for start, end in zip(polygon, polygon[1:] + polygon[:1]):
            distances.append(self._distance_to_segment(point, start, end))
        return min(distances) if distances else math.inf

    def _distance_to_segment(self, point, start, end):
        """Calculate shortest distance from point to one line segment."""
        px, py = point
        sx, sy = start
        ex, ey = end
        dx = ex - sx
        dy = ey - sy

        if dx == 0 and dy == 0:
            return math.dist(point, start)

        ratio = ((px - sx) * dx + (py - sy) * dy) / (dx * dx + dy * dy)
        ratio = max(0, min(1, ratio))
        projection = (sx + ratio * dx, sy + ratio * dy)
        return math.dist(point, projection)

    def _get_level(self, inside):
        """Map inside-zone state to warning level."""
        return "high" if inside else "medium"

    def _update_state(self, track_id, zone, now_seconds, timestamp):
        key = self._state_key(track_id, zone)
        state = self._states.get(key)
        if state is None:
            state = {
                "firstRiskAt": timestamp,
                "firstRiskSeconds": now_seconds,
            }
            self._states[key] = state

        state["lastRiskAt"] = timestamp
        state["lastRiskSeconds"] = now_seconds
        return state

    def _clear_state(self, track_id, zone):
        self._states.pop(self._state_key(track_id, zone), None)

    def _purge_expired(self, now_seconds):
        self._states = {
            key: state
            for key, state in self._states.items()
            if now_seconds - state.get("lastRiskSeconds", now_seconds) <= self.state_ttl_seconds
        }

    def _state_key(self, track_id, zone):
        return str(track_id), str(self._zone_id(zone))

    def _zone_id(self, zone):
        return zone.get("id", zone.get("zoneId"))

    def _min_stay_seconds(self, zone):
        value = zone.get("minStaySeconds", zone.get("staySeconds", zone.get("min_stay_seconds")))
        if value is None:
            value = self.min_stay_seconds
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return self.min_stay_seconds


def _timestamp_seconds(value):
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return datetime.now(timezone.utc).timestamp()

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized).timestamp()
    except ValueError:
        return datetime.now(timezone.utc).timestamp()


def _now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()
