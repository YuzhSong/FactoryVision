from pathlib import Path

from django.conf import settings
from django.utils.text import get_valid_filename
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework import status as http_status
from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.ai_results.models import Alert
from common.response import api_response

from .models import Event
from .serializers import EventListSerializer, EventMediaUploadSerializer, EventPlaceholderSerializer


@extend_schema(
    summary="事件模块占位接口",
    description="返回事件模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: EventPlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Events placeholder",
            value={
                "code": 200,
                "message": "Events module placeholder",
                "data": {"module": "events", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    serializer = EventPlaceholderSerializer()
    return api_response(data=serializer.data, message="Events module placeholder")


@extend_schema(
    summary="List formal events",
    description="Return formal Event records without any AIEvent compatibility data.",
    responses={200: EventListSerializer(many=True)},
)
@api_view(["GET"])
def event_list_view(request):
    events = Event.objects.select_related("camera").all()
    camera_id = request.query_params.get("cameraId")
    if camera_id:
        events = events.filter(camera_id=camera_id)
    return api_response(
        data={"total": events.count(), "items": EventListSerializer(events, many=True).data},
        message="success",
    )


@extend_schema(
    summary="Upload event replay media",
    description="Accept keyframe/clip/manifest files for a formal event and persist browser-accessible media URLs.",
    request=EventMediaUploadSerializer,
    responses={200: EventMediaUploadSerializer, 400: None, 404: None},
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def event_media_upload_view(request, event_id):
    event = Event.objects.filter(id=event_id).first()
    if event is None:
        return api_response(
            code=404,
            message="事件不存在",
            data=None,
            status=http_status.HTTP_404_NOT_FOUND,
        )

    if not any(name in request.FILES for name in ("keyframe", "clip", "manifest")):
        return api_response(
            code=400,
            message="至少需要上传一个媒体文件",
            data=None,
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    media_dir = Path(settings.MEDIA_ROOT) / "events" / str(event.id)
    media_dir.mkdir(parents=True, exist_ok=True)
    media = dict((event.payload or {}).get("media") or {})
    media["status"] = request.data.get("status") or media.get("status") or "uploaded"
    if request.data.get("mediaEventId"):
        media["mediaEventId"] = request.data.get("mediaEventId")

    for field_name, url_key, path_key in (
        ("keyframe", "keyframeUrl", "keyframePath"),
        ("clip", "clipUrl", "clipPath"),
        ("manifest", "manifestUrl", "manifestPath"),
    ):
        uploaded = request.FILES.get(field_name)
        if uploaded is None:
            continue
        filename = _media_filename(field_name, uploaded.name)
        relative_path = f"events/{event.id}/{filename}"
        _save_uploaded_file(media_dir / filename, uploaded)
        media[path_key] = relative_path
        media[url_key] = request.build_absolute_uri(f"{settings.MEDIA_URL}{relative_path}")

    payload = dict(event.payload or {})
    payload["media"] = media
    event.payload = payload
    if media.get("keyframePath"):
        event.snapshot_path = media["keyframePath"]
        event.save(update_fields=["payload", "snapshot_path", "updated_at"])
        Alert.objects.filter(event=event).update(snapshot_path=media["keyframePath"])
    else:
        event.save(update_fields=["payload", "updated_at"])

    return api_response(data=media, message="success")


def _media_filename(field_name, original_name):
    suffix = Path(get_valid_filename(original_name or "")).suffix.lower()
    if field_name == "keyframe":
        return f"keyframe{suffix if suffix in {'.jpg', '.jpeg', '.png', '.webp'} else '.jpg'}"
    if field_name == "clip":
        return f"clip{suffix if suffix in {'.mp4', '.webm', '.mov'} else '.mp4'}"
    return "manifest.json"


def _save_uploaded_file(path, uploaded):
    with path.open("wb") as handle:
        for chunk in uploaded.chunks():
            handle.write(chunk)

# Create your views here.
