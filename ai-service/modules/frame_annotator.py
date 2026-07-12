class FrameAnnotator:
    """Draw AI detection results onto OpenCV frames."""

    def __init__(self, line_width: int = 1, label_scale: float = 0.28):
        self.line_width = max(1, int(line_width))
        self.label_scale = max(0.1, float(label_scale))

    def draw_results(self, frame, results: list[dict]):
        """Draw known bbox results and labels on a frame."""
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to draw detection boxes.") from exc

        output = frame.copy()
        for result in results or []:
            bbox = result.get("bbox")
            if not bbox:
                continue

            x1 = int(bbox.get("x1", 0))
            y1 = int(bbox.get("y1", 0))
            x2 = int(bbox.get("x2", 0))
            y2 = int(bbox.get("y2", 0))
            color = _color_for_result(result)
            label = _label_for_result(result)

            cv2.rectangle(output, (x1, y1), (x2, y2), color, self.line_width)
            if label:
                _draw_label(cv2, output, label, x1, y1, color, self.label_scale)

        return output

    def draw_zones(self, frame, zones: list[dict] | None, results: list[dict] | None = None):
        """Draw enabled/disabled polygon regions before detection boxes are rendered."""
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to draw regions.") from exc

        output = frame.copy()
        height, width = output.shape[:2]
        event_by_region = {
            str(item.get("regionId", item.get("zoneId"))): item
            for item in results or []
            if item.get("type") == "ZONE_WARNING"
        }
        for zone in zones or []:
            if not isinstance(zone, dict):
                continue
            points = zone.get("points") or zone.get("polygonPoints") or []
            if len(points) < 3:
                continue
            coords = []
            for point in points:
                if isinstance(point, dict):
                    x, y = point.get("x", 0), point.get("y", 0)
                elif isinstance(point, (list, tuple)) and len(point) == 2:
                    x, y = point
                else:
                    continue
                x, y = float(x), float(y)
                if 0 <= x <= 1 and 0 <= y <= 1:
                    x, y = x * width, y * height
                coords.append((int(round(x)), int(round(y))))
            if len(coords) < 3:
                continue
            region_id = str(zone.get("id", zone.get("zoneId", zone.get("regionId", ""))))
            enabled = zone.get("enabled", True)
            active_event = event_by_region.get(region_id)
            color = (0, 0, 255) if active_event else ((0, 180, 255) if enabled else (125, 125, 125))
            cv2.polylines(output, [np.asarray(coords, dtype=np.int32)], True, color, self.line_width)
            suffix = "triggered" if active_event else ("enabled" if enabled else "disabled")
            label = f"{zone.get('name', zone.get('zoneName', region_id))} ({suffix})"
            if active_event:
                label = f"{label} {active_event.get('durationSeconds', 0):.1f}s"
            _draw_label(cv2, output, label, coords[0][0], coords[0][1], color, self.label_scale)
        return output

    def draw_test_box(self, frame, frame_id: str | None = None):
        """Draw a deterministic test box for stream pipeline verification."""
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to draw detection boxes.") from exc

        output = frame.copy()
        height, width = output.shape[:2]
        x1 = max(0, int(width * 0.18))
        y1 = max(0, int(height * 0.18))
        x2 = min(width - 1, int(width * 0.48))
        y2 = min(height - 1, int(height * 0.78))
        label = f"TEST BOX {frame_id or ''}".strip()
        color = (0, 255, 0)
        cv2.rectangle(output, (x1, y1), (x2, y2), color, self.line_width)
        _draw_label(cv2, output, label, x1, y1, color, self.label_scale)
        return output

    def draw_debug_overlay(self, frame, metrics: dict | None = None):
        """Draw stream timing metrics in the top-left corner."""
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to draw debug overlay.") from exc

        metrics = metrics or {}
        lines = [
            f"time: {metrics.get('time', '')}",
            f"process_fps: {metrics.get('process_fps', 0)}",
            f"dropped_frames: {metrics.get('dropped_frames', 0)}",
            f"frame_age_ms: {metrics.get('frame_age_ms', 0)}",
            f"playback mode: {metrics.get('playback_mode', 'detected stream')}",
        ]
        output = frame.copy()
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.48
        thickness = 1
        line_height = 20
        padding = 8
        width = 330
        height = padding * 2 + line_height * len(lines)
        cv2.rectangle(output, (0, 0), (width, height), (0, 0, 0), -1)
        for index, line in enumerate(lines):
            y = padding + 15 + index * line_height
            cv2.putText(output, line, (padding, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
        return output


def _label_for_result(result: dict):
    """Create compact display label from one AI result."""
    result_type = result.get("type", "AI")
    helmet_status = result.get("helmetStatus")
    if result_type == "HELMET_DETECTION":
        return _helmet_label(helmet_status, result.get("helmetConfidence"))

    confidence = result.get("confidence")
    track_id = result.get("trackId")
    employee_name = result.get("employeeName") or result.get("name")

    parts = ["Person" if result_type == "PERSON_DETECTION" else result_type.replace("_", " ")]
    if track_id:
        parts.append(str(track_id))
    if employee_name:
        parts.append(str(employee_name))
    if confidence is not None:
        try:
            parts.append(f"{float(confidence):.2f}")
        except (TypeError, ValueError):
            pass
    if result_type == "PERSON_DETECTION":
        parts.append(_helmet_label(helmet_status))
    return " ".join(parts)


def _color_for_result(result: dict):
    """Choose BGR drawing color based on result type."""
    result_type = result.get("type", "")
    if "FACE" in result_type:
        return (255, 180, 0)
    if result_type == "HELMET_DETECTION":
        return (0, 0, 255) if result.get("helmetStatus") == "no_helmet" else (0, 255, 0)
    if "WARNING" in result_type or "ALERT" in result_type:
        return (0, 0, 255)
    return (0, 255, 0)


def _helmet_label(status, confidence=None):
    """Use a consistent, human-readable PPE label for people and helmet boxes."""
    labels = {"helmet": "Helmet", "no_helmet": "No Helmet"}
    label = labels.get(status, "Unknown")
    if confidence is None:
        return label
    try:
        return f"{label} {float(confidence):.2f}"
    except (TypeError, ValueError):
        return label


def _draw_label(cv2, frame, label: str, x: int, y: int, color, scale: float = 0.28):
    """Draw readable label background and text."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(label, font, scale, thickness)
    top = max(0, y - text_height - baseline - 6)
    bottom = top + text_height + baseline + 6
    right = x + text_width + 8
    cv2.rectangle(frame, (x, top), (right, bottom), color, -1)
    cv2.putText(frame, label, (x + 4, bottom - baseline - 3), font, scale, (0, 0, 0), thickness, cv2.LINE_AA)
