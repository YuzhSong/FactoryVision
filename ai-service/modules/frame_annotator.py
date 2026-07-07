class FrameAnnotator:
    """Draw AI detection results onto OpenCV frames."""

    def __init__(self, line_width: int = 2):
        self.line_width = line_width

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
                _draw_label(cv2, output, label, x1, y1, color)

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
        _draw_label(cv2, output, label, x1, y1, color)
        return output


def _label_for_result(result: dict):
    """Create compact display label from one AI result."""
    result_type = result.get("type", "AI")
    confidence = result.get("confidence")
    track_id = result.get("trackId")
    employee_name = result.get("employeeName") or result.get("name")

    parts = [result_type.replace("_", " ")]
    if track_id:
        parts.append(str(track_id))
    if employee_name:
        parts.append(str(employee_name))
    if confidence is not None:
        try:
            parts.append(f"{float(confidence):.2f}")
        except (TypeError, ValueError):
            pass
    return " ".join(parts)


def _color_for_result(result: dict):
    """Choose BGR drawing color based on result type."""
    result_type = result.get("type", "")
    if "FACE" in result_type:
        return (255, 180, 0)
    if "WARNING" in result_type or "ALERT" in result_type:
        return (0, 0, 255)
    return (0, 255, 0)


def _draw_label(cv2, frame, label: str, x: int, y: int, color):
    """Draw readable label background and text."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.55
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(label, font, scale, thickness)
    top = max(0, y - text_height - baseline - 6)
    bottom = top + text_height + baseline + 6
    right = x + text_width + 8
    cv2.rectangle(frame, (x, top), (right, bottom), color, -1)
    cv2.putText(frame, label, (x + 4, bottom - baseline - 3), font, scale, (0, 0, 0), thickness, cv2.LINE_AA)
