from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.cameras.models import Camera
from apps.cameras.serializers import CameraListSerializer
from apps.employees.models import Employee
from apps.employees.serializers import EmployeeListSerializer
from apps.events.models import Event
from apps.zones.models import Zone
from apps.zones.serializers import ZoneListSerializer
from common.response import api_response

from .models import AIEvent, Alert
from .serializers import AIResultPlaceholderSerializer, AIResultReportSerializer, HealthCheckSerializer


ALERT_EVENT_TYPES = {
    "HELMET_WARNING",
    "STRANGER_DETECTED",
    "STRANGER_ALERT",
    "EMPLOYEE_ABSENT",
    "EMPLOYEE_RETURNED",
    "FALL_DETECTED",
    "FALL_ALERT",
    "ZONE_INTRUSION",
    "ZONE_WARNING",
    "RUNNING_ALERT",
    "NO_HELMET",
}

DEFAULT_THRESHOLDS = {
    "helmet": {"confidence": 0.6, "warning": 0.8},
    "fall": {"confidence": 0.6},
    "stranger": {"similarity": 0.45},
    "face": {"similarity": 0.45},
}


@extend_schema(
    summary="AI 结果模块占位接口",
    description="返回 AI 结果模块当前占位状态，用于确认路由和模块边界存在。",
    responses={
        200: AIResultPlaceholderSerializer,
    },
    examples=[
        OpenApiExample(
            "AI results placeholder",
            value={
                "code": 200,
                "message": "AI results module placeholder",
                "data": {"module": "ai_results", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    serializer = AIResultPlaceholderSerializer()
    return api_response(data=serializer.data, message="AI results module placeholder")


@extend_schema(
    summary="上报 AI 分析结果",
    description="AI 服务向后端上报单帧检测结果。当前接口校验 payload，并返回已接收结果数量。",
    request=AIResultReportSerializer,
    responses={
        200: None,
        400: None,
    },
    examples=[
        OpenApiExample(
            "AI report request",
            value={
                "cameraId": 1,
                "frameId": "frame-001",
                "timestamp": "2026-07-08T10:00:00+08:00",
                "results": [
                    {
                        "type": "PERSON_DETECTION",
                        "trackId": "t-1",
                        "bbox": {"x": 120, "y": 80, "w": 180, "h": 320},
                    }
                ],
            },
            request_only=True,
        ),
        OpenApiExample(
            "AI report response",
            value={
                "code": 200,
                "message": "AI results accepted",
                "data": {
                    "eventIds": [1],
                    "aiEventIds": [1],
                    "alertIds": [],
                    "acceptedResults": 1,
                    "cameraId": 1,
                    "frameId": "frame-001",
                },
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["POST"])
def report_ai_results(request):
    serializer = AIResultReportSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="Invalid AI report payload",
            data=serializer.errors,
            status=400,
        )

    validated = serializer.validated_data
    camera = _find_camera(validated["cameraId"])
    if camera is None:
        return api_response(
            code=400,
            message="Invalid AI report payload",
            data={"cameraId": ["Camera does not exist."]},
            status=400,
        )

    event_ids = []
    ai_event_ids = []
    alert_ids = []
    rejected_results = 0

    with transaction.atomic():
        for result in validated["results"]:
            result_type = str(result.get("type") or "").strip()
            if not result_type:
                rejected_results += 1
                continue

            event = Event.objects.create(
                camera=camera,
                camera_identifier=str(validated["cameraId"]),
                frame_id=validated.get("frameId", ""),
                event_type=result_type,
                source=Event.Source.AI_SERVICE,
                severity=_event_severity(result_type, result),
                status=Event.Status.NEW,
                occurred_at=validated["timestamp"],
                track_id=_extract_track_id(result),
                bbox=_extract_bbox(result),
                confidence=_extract_confidence(result),
                snapshot_path=_extract_snapshot_path(result, validated.get("eventMedia", [])),
                payload=result,
            )
            event_ids.append(event.id)

            ai_event = AIEvent.objects.create(
                camera=camera,
                camera_identifier=str(validated["cameraId"]),
                frame_id=event.frame_id,
                event_type=event.event_type,
                confidence=event.confidence,
                bbox=event.bbox,
                snapshot_path=event.snapshot_path,
                payload=result,
                occurred_at=event.occurred_at,
            )
            ai_event_ids.append(ai_event.id)

            if _should_create_alert(result_type):
                alert = Alert.objects.create(
                    event=ai_event,
                    system_event=event,
                    camera=camera,
                    event_type=result_type,
                    level=str(result.get("level") or _default_level(result_type)),
                    title=_alert_title(result_type),
                    description=_alert_description(result),
                    snapshot_path=event.snapshot_path,
                    occurred_at=event.occurred_at,
                )
                alert_ids.append(alert.id)

    return api_response(
        code=200,
        message="AI results accepted",
        data={
            "eventIds": event_ids,
            "aiEventIds": ai_event_ids,
            "alertIds": alert_ids,
            "acceptedResults": len(event_ids),
            "rejectedResults": rejected_results,
            "cameraId": validated["cameraId"],
            "frameId": validated.get("frameId", ""),
        },
    )


@extend_schema(
    summary="AI service bootstrap",
    description="Aggregate cameras, zones, employees, and thresholds for ai-service startup cache.",
    responses={200: None},
)
@api_view(["GET"])
def ai_bootstrap(_request):
    cameras = Camera.objects.all()
    zones = Zone.objects.select_related("camera").all()
    employees = Employee.objects.prefetch_related("face_features").all()
    return api_response(
        data={
            "cameras": CameraListSerializer(cameras, many=True).data,
            "zones": ZoneListSerializer(zones, many=True).data,
            "employees": [_serialize_employee_for_bootstrap(employee) for employee in employees],
            "thresholds": DEFAULT_THRESHOLDS,
            "timestamp": timezone.now().isoformat(),
        },
        message="success",
    )


@extend_schema(
    summary="后端健康检查",
    description="返回后端服务健康状态。",
    responses={
        200: HealthCheckSerializer,
    },
    examples=[
        OpenApiExample(
            "Health check",
            value={
                "code": 200,
                "message": "Backend service is healthy",
                "data": {"service": "backend", "status": "ok", "stage": "skeleton"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def health_check(_request):
    serializer = HealthCheckSerializer()
    return api_response(data=serializer.data, message="Backend service is healthy")


def _find_camera(camera_id):
    if str(camera_id).isdigit():
        camera = Camera.objects.filter(id=int(camera_id)).first()
        if camera:
            return camera
    return Camera.objects.filter(code=str(camera_id)).first()


def _extract_confidence(result):
    for key in ("confidence", "helmetConfidence", "score", "similarity"):
        value = result.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _extract_bbox(result):
    bbox = result.get("bbox") or result.get("box") or {}
    return bbox if isinstance(bbox, dict) else {}


def _extract_track_id(result):
    value = result.get("trackId") or result.get("track_id") or result.get("id")
    return "" if value is None else str(value)


def _extract_snapshot_path(result, event_media):
    for key in ("snapshotPath", "snapshotUrl", "imagePath"):
        value = result.get(key)
        if value:
            return str(value)

    event_id = result.get("eventId")
    for media in event_media or []:
        if event_id and str(media.get("eventId")) != str(event_id):
            continue
        value = media.get("snapshotPath") or media.get("snapshotUrl")
        if value:
            return str(value)
    return ""


def _should_create_alert(result_type):
    return result_type in ALERT_EVENT_TYPES or result_type.endswith("_WARNING") or result_type.endswith("_ALERT")


def _default_level(result_type):
    if result_type in {"FALL_DETECTED", "FALL_ALERT", "ZONE_INTRUSION", "STRANGER_DETECTED", "STRANGER_ALERT"}:
        return "high"
    if result_type == "EMPLOYEE_RETURNED":
        return "low"
    return "medium"


def _event_severity(result_type, result):
    level = str(result.get("level") or "").lower()
    if level in {choice.value for choice in Event.Severity}:
        return level
    if _should_create_alert(result_type):
        return _default_level(result_type)
    return Event.Severity.INFO


def _alert_title(result_type):
    return result_type.replace("_", " ").title()


def _alert_description(result):
    track_id = result.get("trackId")
    zone_name = result.get("zoneName")
    name = result.get("name") or result.get("employeeName")
    parts = []
    if track_id:
        parts.append(f"trackId={track_id}")
    if zone_name:
        parts.append(f"zone={zone_name}")
    if name:
        parts.append(f"name={name}")
    return ", ".join(parts)


def _serialize_employee_for_bootstrap(employee):
    data = EmployeeListSerializer(employee).data
    data["faceFeatures"] = [
        {
            "id": feature.id,
            "featureVector": feature.feature_vector,
            "imagePath": feature.image_path,
            "faceType": feature.face_type,
        }
        for feature in employee.face_features.all()
    ]
    return data

# Create your views here.
