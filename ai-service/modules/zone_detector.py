import math


class ZoneDetector:
    """Detect zone intrusion from person foot points and polygon zones."""

    def __init__(self, zones=None):
        """Initialize zone detector with optional zones."""
        self.zones = []
        if zones:
            self.set_zones(zones)

    def set_zones(self, zones):
        """Replace active warning zone definitions."""
        self.zones = zones or []

    def detect_intrusion(self, detections):
        """Return ZONE_WARNING results for detections inside or near zones."""
        warnings = []
        for detection in detections or []:
            foot_point = self._get_foot_point(detection)
            if foot_point is None:
                continue

            for zone in self.zones:
                points = self._get_zone_points(zone)
                if len(points) < 3:
                    continue

                inside = self._point_in_polygon(foot_point, points)
                distance = 0 if inside else self._distance_to_polygon(foot_point, points)
                safe_distance = zone.get("safeDistance", zone.get("safe_distance", 0)) or 0

                if inside or distance <= safe_distance:
                    warnings.append(
                        {
                            "type": "ZONE_WARNING",
                            "trackId": detection.get("trackId"),
                            "zoneId": zone.get("id", zone.get("zoneId")),
                            "zoneName": zone.get("name", zone.get("zoneName")),
                            "footPoint": {"x": foot_point[0], "y": foot_point[1]},
                            "inside": inside,
                            "distance": round(distance, 2),
                            "safeDistance": safe_distance,
                            "level": self._get_level(inside),
                        }
                    )

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
