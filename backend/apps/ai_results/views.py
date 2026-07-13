import logging
import threading
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncHour
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework import status as http_status
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from apps.ai_results.services.dingtalk import DingTalkNotificationError, DingTalkNotifier
from apps.cameras.models import Camera
from apps.cameras.serializers import CameraListSerializer
from apps.employees.models import Employee
from apps.employees.serializers import EmployeeListSerializer
from apps.events.models import Event
from apps.zones.models import Zone
from apps.zones.serializers import ZoneListSerializer
from common.response import api_response

from .models import Alert

logger = logging.getLogger(__name__)

from .serializers import (
    AIResultPlaceholderSerializer,
    AIResultReportSerializer,
    AlertHandleSerializer,
    AlertSerializer,
    DashboardSummarySerializer,
    HealthCheckSerializer,
)

FORMAL_ACTIONABLE_EVENT_TYPES = {
    "helmet_violation",
    "region_intrusion",
    "region_dwell",
    "face_recognized",
    "stranger_detected",
    "fall_detected",
}

EVENT_INTERNAL_TYPES = {
    "helmet_violation": {"HELMET_WARNING", "helmet_violation"},
    "region_intrusion": {"ZONE_WARNING", "region_intrusion"},
    "region_dwell": {"ZONE_WARNING", "region_dwell"},
    "face_recognized": {"FACE_RECOGNIZED", "FACE_RESULT", "face_recognized"},
    "stranger_detected": {"STRANGER_DETECTED", "STRANGER_ALERT", "stranger_detected"},
    "fall_detected": {"FALL_DETECTED", "FALL_ALERT", "fall_detected"},
}

EVENT_DEDUP_SECONDS = {
    "helmet_violation": 20,
    "face_recognized": 60,
    "stranger_detected": 30,
    "fall_detected": 30,
}


# 会触发告警（并推送钉钉）的事件类型，均为 _normalize_event_type 归一化后的小写别名。
ALERT_TRIGGER_TYPES = {
    "helmet_violation",
    "region_intrusion",
    "region_dwell",
    "stranger_detected",
    "fall_detected",
}

DEFAULT_THRESHOLDS = {
    "helmet": {"confidence": 0.6, "warning": 0.8},
    "fall": {"confidence": 0.6},
    "stranger": {"similarity": 0.45},
    "face": {"similarity": 0.45},
}

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
RECENT_ALERT_LIMIT = 5


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
    alert_ids = []
    rejected_results = 0
    _pushed_face_keys = set()

    with transaction.atomic():
        for result in validated["results"]:
            result_type = _normalize_event_type(result)
            if result_type not in FORMAL_ACTIONABLE_EVENT_TYPES or not _is_actionable_result(result_type, result):
                rejected_results += 1
                continue

            track_id = _extract_track_id(result)
            if _is_duplicate_event(camera, result_type, result, validated["timestamp"], track_id):
                rejected_results += 1
                logger.info(
                    "Duplicate AI event suppressed camera_id=%s event_type=%s track_id=%s",
                    validated["cameraId"],
                    result_type,
                    track_id,
                )
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
                track_id=track_id,
                bbox=_extract_bbox(result),
                confidence=_extract_confidence(result),
                snapshot_path=_extract_snapshot_path(result, validated.get("eventMedia", [])),
                payload=result,
            )
            event_ids.append(event.id)
            event_description = _alert_description(result)

            should_push = _should_create_alert(result_type) or result_type == "face_recognized"
            if result_type == "face_recognized" and result.get("employeeId"):
                # 同一员工同一 trackId 只推一次
                key = (event.track_id, str(result["employeeId"]))
                if key not in _pushed_face_keys:
                    _pushed_face_keys.add(key)
                    should_push = True

            if should_push:
                # 推 WebSocket：告警级事件 + 员工首次识别（供考勤/实时事件流使用）
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        f"realtime_{validated['cameraId']}",
                        {
                            "type": "event.message",
                            "data": {
                                "type": "EVENT_CREATED",
                                "cameraId": validated["cameraId"],
                                "timestamp": str(validated["timestamp"]),
                                "payload": {
                                    "eventId": event.id,
                                    "eventType": event.event_type,
                                    "severity": event.severity,
                                    "trackId": event.track_id,
                                    "bbox": event.bbox,
                                    "confidence": event.confidence,
                                    "name": result.get("name") or result.get("employeeName"),
                                    "employeeName": result.get("employeeName") or result.get("name"),
                                    "employeeId": result.get("employeeId"),
                                    "description": event_description,
                                    "occurredAt": str(event.occurred_at),
                                },
                            },
                        },
                    )
                except Exception:
                    logger.exception(
                        "WebSocket event broadcast failed group=realtime_%s event_id=%s event_type=%s",
                        validated["cameraId"],
                        event.id,
                        event.event_type,
                    )

            if _should_create_alert(result_type):
                alert = Alert.objects.create(
                    event=event,
                    camera=camera,
                    event_type=result_type,
                    level=str(result.get("level") or _default_level(result_type)),
                    title=_alert_title(result_type),
                    description=event_description,
                    snapshot_path=event.snapshot_path,
                    occurred_at=event.occurred_at,
                )
                alert_ids.append(alert.id)
                transaction.on_commit(lambda a=alert: _notify_dingtalk_alert(a))

    return api_response(
        code=200,
        message="AI results accepted",
        data={
            "eventIds": event_ids,
            "alertIds": alert_ids,
            "acceptedResults": len(event_ids),
            "rejectedResults": rejected_results,
            "cameraId": validated["cameraId"],
            "frameId": validated.get("frameId", ""),
        },
    )


def _parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


@extend_schema(
    summary="查询告警列表",
    description="查询告警中心列表，支持关键词（标题）、等级、状态、摄像头和时间范围筛选，支持分页。",
    parameters=[
        OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，正整数，默认 1"),
        OpenApiParameter("pageSize", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页数量，1~100，默认 20"),
        OpenApiParameter("keyword", OpenApiTypes.STR, OpenApiParameter.QUERY, description="关键词，模糊搜索告警标题"),
        OpenApiParameter("severity", OpenApiTypes.STR, OpenApiParameter.QUERY, description="等级：info/low/medium/high"),
        OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, description="状态：pending/processing/closed"),
        OpenApiParameter("cameraId", OpenApiTypes.INT, OpenApiParameter.QUERY, description="摄像头 ID"),
        OpenApiParameter("startTime", OpenApiTypes.STR, OpenApiParameter.QUERY, description="开始时间，ISO 格式"),
        OpenApiParameter("endTime", OpenApiTypes.STR, OpenApiParameter.QUERY, description="结束时间，ISO 格式"),
    ],
    responses={200: AlertSerializer(many=True), 400: None},
    examples=[
        OpenApiExample(
            "告警列表响应",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "total": 1,
                    "items": [
                        {
                            "id": 1,
                            "title": "危险区域入侵",
                            "eventType": "ZONE_INTRUSION",
                            "severity": "high",
                            "status": "pending",
                            "cameraId": 1,
                            "cameraName": "一号车间入口",
                            "occurredAt": "2026-07-10T14:05:03+08:00",
                            "description": "trackId t-1 进入 危险设备区",
                        }
                    ],
                },
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
@api_view(["GET"])
def alert_list_view(request):
    page = _parse_positive_int(request.query_params.get("page", 1))
    page_size = _parse_positive_int(request.query_params.get("pageSize", DEFAULT_PAGE_SIZE))
    camera_id = request.query_params.get("cameraId")

    if page is None or page_size is None or page_size > MAX_PAGE_SIZE:
        return api_response(
            code=400,
            message="分页参数必须为正整数，pageSize 不超过 100",
            data=None,
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    if camera_id and not str(camera_id).isdigit():
        return api_response(
            code=400,
            message="cameraId 必须为正整数",
            data=None,
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    alerts = Alert.objects.select_related("event", "camera").all()

    keyword = request.query_params.get("keyword")
    severity = request.query_params.get("severity")
    alert_status = request.query_params.get("status")
    start_time = request.query_params.get("startTime")
    end_time = request.query_params.get("endTime")

    if keyword:
        alerts = alerts.filter(title__icontains=keyword)
    if severity:
        alerts = alerts.filter(event__severity=severity)
    if alert_status:
        alerts = alerts.filter(status=alert_status)
    if camera_id:
        alerts = alerts.filter(camera_id=int(camera_id))
    if start_time:
        alerts = alerts.filter(occurred_at__gte=start_time)
    if end_time:
        alerts = alerts.filter(occurred_at__lte=end_time)

    total = alerts.count()
    start = (page - 1) * page_size
    items = AlertSerializer(alerts[start:start + page_size], many=True).data
    return api_response(data={"total": total, "items": items}, message="success")


@extend_schema(
    summary="处置告警",
    description="更新告警状态（pending→processing→closed）。该接口需要 Bearer JWT 认证。",
    request=AlertHandleSerializer,
    responses={200: AlertSerializer, 400: None, 404: None},
    examples=[
        OpenApiExample(
            "处置请求",
            value={"status": "processing"},
            request_only=True,
        ),
        OpenApiExample(
            "处置成功",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "id": 1,
                    "title": "危险区域入侵",
                    "eventType": "ZONE_INTRUSION",
                    "severity": "high",
                    "status": "processing",
                    "cameraId": 1,
                    "cameraName": "一号车间入口",
                    "occurredAt": "2026-07-10T14:05:03+08:00",
                    "description": "",
                },
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "告警不存在",
            value={"code": 404, "message": "告警不存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["POST"])
def alert_handle_view(request, alert_id):
    serializer = AlertHandleSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=http_status.HTTP_400_BAD_REQUEST,
        )

    alert = Alert.objects.select_related("event", "camera").filter(id=alert_id).first()
    if alert is None:
        return api_response(
            code=404,
            message="告警不存在",
            data=None,
            status=http_status.HTTP_404_NOT_FOUND,
        )

    alert.status = serializer.validated_data["status"]
    alert.save(update_fields=["status"])
    return api_response(data=AlertSerializer(alert).data, message="success")


@extend_schema(
    summary="Dashboard summary",
    description="Return database-backed operational counts, recent alerts, and today's hourly event trend.",
    responses={200: DashboardSummarySerializer},
)
@api_view(["GET"])
def dashboard_summary_view(_request):
    today = timezone.localdate()
    today_events = Event.objects.filter(occurred_at__date=today)
    today_alerts = Alert.objects.filter(occurred_at__date=today)
    event_trend = (
        today_events.annotate(hour=TruncHour("occurred_at", tzinfo=timezone.get_current_timezone()))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )
    recent_alerts = Alert.objects.select_related("event", "camera").all()[:RECENT_ALERT_LIMIT]
    summary = {
        "cameraCount": Camera.objects.count(),
        "onlineCameraCount": Camera.objects.filter(status=Camera.Status.ONLINE).count(),
        "employeeCount": Employee.objects.count(),
        "todayEventCount": today_events.count(),
        "todayAlertCount": today_alerts.count(),
        "pendingAlertCount": Alert.objects.filter(status=Alert.Status.PENDING).count(),
        "recentAlerts": recent_alerts,
        "eventTrend": list(event_trend),
    }
    return api_response(data=DashboardSummarySerializer(summary).data, message="success")


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
    bbox = result.get("bbox") or result.get("faceBox") or result.get("box") or {}
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
    return result_type in ALERT_TRIGGER_TYPES


def _is_actionable_result(result_type, result):
    internal_type = str(result.get("type") or result.get("eventType") or "").strip()
    if internal_type not in EVENT_INTERNAL_TYPES.get(result_type, set()):
        return False
    if result_type == "face_recognized":
        return bool(result.get("employeeId")) and (
            result.get("type") == "FACE_RECOGNIZED" or result.get("matched") is True
        )
    if result_type == "stranger_detected":
        return result.get("matched") is not True
    return True


def _is_duplicate_event(camera, result_type, result, occurred_at, track_id):
    events = Event.objects.filter(camera=camera, event_type=result_type)
    if result_type == "face_recognized":
        employee_id = result.get("employeeId")
        if employee_id in (None, ""):
            return False
        return events.filter(
            occurred_at__gte=occurred_at - timedelta(seconds=EVENT_DEDUP_SECONDS[result_type]),
            payload__employeeId=employee_id,
        ).exists()

    if result_type in {"region_intrusion", "region_dwell"}:
        region_id = result.get("regionId", result.get("zoneId"))
        entered_at = result.get("enteredAt")
        if region_id not in (None, "") and entered_at:
            return events.filter(
                track_id=track_id,
                payload__regionId=region_id,
                payload__enteredAt=entered_at,
            ).exists()
        return False

    cooldown = EVENT_DEDUP_SECONDS.get(result_type)
    if not cooldown or not track_id:
        return False
    return events.filter(
        track_id=track_id,
        occurred_at__gte=occurred_at - timedelta(seconds=cooldown),
    ).exists()


def _normalize_event_type(result):
    internal = str(result.get("type") or "").strip()
    nested = str(result.get("eventType") or "").strip()
    if internal == "ZONE_WARNING":
        return nested if nested in {"region_intrusion", "region_dwell"} else "region_intrusion"
    aliases = {
        "HELMET_WARNING": "helmet_violation",
        "FACE_RESULT": "face_recognized",
        "FACE_RECOGNIZED": "face_recognized",
        "STRANGER_DETECTED": "stranger_detected",
        "STRANGER_ALERT": "stranger_detected",
        "FALL_DETECTED": "fall_detected",
        "FALL_ALERT": "fall_detected",
    }
    return aliases.get(nested) or aliases.get(internal) or nested or internal


def _default_level(result_type):
    if result_type in {"FALL_DETECTED", "FALL_ALERT", "ZONE_INTRUSION", "region_intrusion", "STRANGER_DETECTED", "STRANGER_ALERT"}:
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
    if _normalize_event_type(result) == "face_recognized":
        name = result.get("name") or result.get("employeeName") or "Unknown"
        confidence = _extract_confidence(result)
        if confidence is None:
            return str(name)
        if confidence <= 1.0:
            return f"{name} 置信度 {confidence * 100:.1f}%"
        return f"{name} 置信度 {confidence:.1f}%"

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


_ALERT_LEVEL_DISPLAY = {
    "low": "低",
    "medium": "中",
    "high": "高",
    "info": "信息",
}

_ALERT_TYPE_DISPLAY = {
    "helmet_violation": "未佩戴安全帽",
    "region_intrusion": "区域闯入",
    "region_dwell": "区域滞留",
    "stranger_detected": "陌生人闯入",
    "fall_detected": "人员跌倒",
}


def _alert_type_display(alert: Alert) -> str:
    return _ALERT_TYPE_DISPLAY.get(alert.event_type, alert.title)


def _is_alert_handled(alert: Alert) -> bool:
    return alert.status != Alert.Status.PENDING


def _notify_dingtalk_alert(alert: Alert) -> None:
    """Send DingTalk notification after alert creation.

    Notification failures must not break AI result reporting or database writes.
    """
    from django.conf import settings

    if alert.event_type not in ALERT_TRIGGER_TYPES:
        return

    try:
        DingTalkNotifier().send_alert(
            alert_title=_alert_type_display(alert),
            level=_ALERT_LEVEL_DISPLAY.get(alert.level, alert.level),
            content=alert.description or alert.title,
            occurred_at=alert.occurred_at.isoformat() if alert.occurred_at else None,
            camera_name=alert.camera.name if alert.camera else None,
            location=alert.camera.location if alert.camera else None,
            responsible_name=settings.DINGTALK_RESPONSIBLE_NAME or None,
            responsible_mobile=settings.DINGTALK_RESPONSIBLE_MOBILE or None,
        )
    except DingTalkNotificationError:
        logger.exception("DingTalk initial notification failed alert_id=%s", alert.id)
    except Exception:
        logger.exception("Unexpected DingTalk initial notification error alert_id=%s", alert.id)

    escalation_seconds = settings.DINGTALK_ESCALATION_SECONDS
    if escalation_seconds < 1:
        return

    timer = threading.Timer(escalation_seconds, _escalate_alert, args=[alert.id])
    timer.daemon = True
    timer.start()


def _escalate_alert(alert_id: int) -> None:
    from django.conf import settings

    alert = Alert.objects.filter(id=alert_id).select_related("camera").first()
    if alert is None or _is_alert_handled(alert) or alert.event_type not in ALERT_TRIGGER_TYPES:
        return

    try:
        DingTalkNotifier().send_alert(
            alert_title=f"[告警升级] {_alert_type_display(alert)}",
            level=_ALERT_LEVEL_DISPLAY.get(alert.level, alert.level),
            content=alert.description or alert.title,
            occurred_at=alert.occurred_at.isoformat() if alert.occurred_at else None,
            camera_name=alert.camera.name if alert.camera else None,
            location=alert.camera.location if alert.camera else None,
            responsible_name=settings.DINGTALK_LEADER_NAME or None,
            responsible_mobile=settings.DINGTALK_LEADER_MOBILE or None,
        )
    except DingTalkNotificationError:
        logger.exception("DingTalk escalation failed alert_id=%s", alert_id)
    except Exception:
        logger.exception("Unexpected DingTalk escalation error alert_id=%s", alert_id)

# Create your views here.
