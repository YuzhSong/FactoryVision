"""Resolve the single stream-start payload shared by every client path."""

from urllib.parse import urlparse

from django.conf import settings

from apps.zones.models import Zone
from apps.zones.serializers import ZoneListSerializer


def resolve_stream_start_config(camera) -> dict:
    """Build a fully resolved, browser-safe stream configuration for one camera."""
    output_url = _build_processed_output_url(camera)
    return {
        "configVersion": 1,
        "cameraId": camera.id,
        "inputUrl": camera.stream_url,
        "outputUrl": output_url,
        "playUrl": _build_processed_play_url(camera, output_url),
        "includeFaces": bool(camera.include_faces),
        "reportToBackend": True,
        "personDetectInterval": _positive_setting("AI_STREAM_PERSON_DETECT_INTERVAL", 5),
        "helmetDetectInterval": _positive_setting("AI_STREAM_HELMET_DETECT_INTERVAL", 8),
        "helmetDetectOffset": _non_negative_setting("AI_STREAM_HELMET_DETECT_OFFSET", 4),
        "faceDetectInterval": _positive_setting("AI_STREAM_FACE_DETECT_INTERVAL", 30),
        "faceDetectOffset": _non_negative_setting("AI_STREAM_FACE_DETECT_OFFSET", 2),
        "zoneRefreshIntervalSeconds": _positive_float_setting("AI_STREAM_ZONE_REFRESH_INTERVAL_SECONDS", 10.0),
        "reconnectAttempts": _positive_setting("AI_STREAM_RECONNECT_ATTEMPTS", 3),
        "reconnectDelaySeconds": _positive_float_setting("AI_STREAM_RECONNECT_DELAY_SECONDS", 1.0),
        "zones": ZoneListSerializer(Zone.objects.filter(camera=camera), many=True).data,
    }


def _build_processed_output_url(camera) -> str:
    processed_url = (camera.processed_stream_url or "").strip()
    if processed_url.startswith(("rtmp://", "rtmps://")):
        return processed_url
    parsed = urlparse((camera.stream_url or "").strip())
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"rtmp", "rtmps"} or not parsed.netloc or not path_parts:
        return processed_url
    path_parts[-1] = f"{path_parts[-1]}_detected"
    return f"{parsed.scheme}://{parsed.netloc}/{'/'.join(path_parts)}"


def _build_processed_play_url(camera, output_url: str) -> str:
    processed_url = (camera.processed_stream_url or "").strip()
    if processed_url:
        return processed_url
    parsed = urlparse(output_url or "")
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme in {"rtmp", "rtmps"} and parsed.netloc and len(path_parts) >= 2:
        return f"https://{parsed.hostname}:8443/{path_parts[-2]}/{path_parts[-1]}.flv"
    return output_url


def _positive_setting(name: str, default: int) -> int:
    try:
        return max(1, int(getattr(settings, name, default)))
    except (TypeError, ValueError):
        return default


def _non_negative_setting(name: str, default: int) -> int:
    try:
        return max(0, int(getattr(settings, name, default)))
    except (TypeError, ValueError):
        return default


def _positive_float_setting(name: str, default: float) -> float:
    try:
        return max(0.01, float(getattr(settings, name, default)))
    except (TypeError, ValueError):
        return default
