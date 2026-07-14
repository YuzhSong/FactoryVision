from pathlib import Path
from datetime import date

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.ai_results.models import Alert
from common.response import api_response

from .models import MonitorReport
from .serializers import ReportDetailSerializer, ReportListItemSerializer
from .services import REPORT_PERIODS, generate_monitor_report, period_for_label

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def _parse_positive_int(value, default):
    try:
        parsed = int(value if value not in (None, "") else default)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _serialize_report(report):
    return {
        "id": report.id,
        "reportDate": report.report_date,
        "periodLabel": report.period_label,
        "periodStart": report.period_start,
        "periodEnd": report.period_end,
        "alertCount": report.alert_count,
        "highAlertCount": report.high_alert_count,
        "pendingAlertCount": report.pending_alert_count,
        "status": report.status,
        "aiSummary": report.ai_summary,
        "documentPath": report.document_path,
        "generatedAt": report.generated_at,
    }


def _alert_items(report):
    alerts = Alert.objects.select_related("camera").filter(
        occurred_at__gte=report.period_start,
        occurred_at__lt=report.period_end,
    )
    return [
        {
            "id": alert.id,
            "title": alert.title,
            "eventType": alert.event_type,
            "level": alert.level,
            "status": alert.status,
            "cameraId": alert.camera_id,
            "cameraName": alert.camera.name if alert.camera else "未关联摄像头",
            "occurredAt": alert.occurred_at.isoformat(),
            "description": alert.description,
            "keyframePath": _alert_keyframe_path(alert),
            "keyframeUrl": _media_url(_alert_keyframe_path(alert)),
        }
        for alert in alerts
    ]


@extend_schema(
    summary="查询 AI 监控日报列表",
    description="查询已生成的一天一份 AI 监控日报。该接口需要 Bearer JWT 认证。",
    parameters=[
        OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，默认 1"),
        OpenApiParameter("pageSize", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页数量，默认 20，最大 100"),
    ],
    responses={200: ReportListItemSerializer(many=True), 400: None, 401: None},
    examples=[
        OpenApiExample(
            "日报列表",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "total": 1,
                    "items": [
                        {
                            "id": 1,
                            "reportDate": "2026-07-13",
                            "alertCount": 5,
                            "highAlertCount": 1,
                            "pendingAlertCount": 2,
                            "status": "generated",
                            "aiSummary": "本周期共记录 5 条告警。",
                            "documentPath": "reports/monitor-report-2026-07-13.docx",
                            "generatedAt": "2026-07-13T12:00:10+08:00",
                        }
                    ],
                },
                "requestId": "uuid",
            },
            response_only=True,
        )
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_list_view(request):
    page = _parse_positive_int(request.query_params.get("page"), 1)
    page_size = _parse_positive_int(request.query_params.get("pageSize"), DEFAULT_PAGE_SIZE)
    if page is None or page_size is None or page_size > MAX_PAGE_SIZE:
        return api_response(
            code=400,
            message="分页参数必须为正整数，pageSize 不超过 100",
            data=None,
            status=status.HTTP_400_BAD_REQUEST,
        )

    reports = MonitorReport.objects.all()
    report_date = request.query_params.get("date")
    if report_date:
        try:
            parsed_date = date.fromisoformat(report_date)
        except ValueError:
            return api_response(
                code=400,
                message="date 必须使用 YYYY-MM-DD 格式",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )
        reports = reports.filter(report_date=parsed_date)
    period_label = request.query_params.get("periodLabel")
    if period_label:
        reports = reports.filter(period_label=period_label)
    total = reports.count()
    start = (page - 1) * page_size
    items = [_serialize_report(report) for report in reports[start:start + page_size]]
    serializer = ReportListItemSerializer(items, many=True)
    return api_response(data={"total": total, "items": serializer.data}, message="success")


@extend_schema(
    summary="手动生成 AI 监控日报",
    description="按日报日期手动触发生成，用于调试或补生成。未传 reportDate 时生成当天日报。该接口需要 Bearer JWT 认证。",
    request=None,
    responses={200: ReportDetailSerializer, 400: None, 401: None},
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report_generate_view(request):
    report_date_value = request.data.get("reportDate") if isinstance(request.data, dict) else None
    period_label = request.data.get("periodLabel") if isinstance(request.data, dict) else None
    try:
        report_date = date.fromisoformat(report_date_value) if report_date_value else None
    except ValueError:
        return api_response(
            code=400,
            message="reportDate 必须使用 YYYY-MM-DD 格式",
            data=None,
            status=status.HTTP_400_BAD_REQUEST,
        )
    today = timezone.localdate()
    if report_date and report_date > today:
        return api_response(
            code=400,
            message="不能生成未来日期的日报",
            data=None,
            status=status.HTTP_400_BAD_REQUEST,
        )

    if period_label and period_label not in REPORT_PERIODS:
        return api_response(
            code=400,
            message="periodLabel 必须是 00:00-06:00、06:00-12:00、12:00-18:00 或 18:00-24:00",
            data=None,
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_date = report_date or today
    if period_label:
        period_start, period_end, _label = period_for_label(target_date, period_label)
        if period_end > timezone.now():
            return api_response(
                code=400,
                message="不能生成尚未结束时段的报告",
                data=None,
                status=status.HTTP_400_BAD_REQUEST,
            )
        report = generate_monitor_report(target_date, period_label=period_label)
    else:
        report = generate_monitor_report()
    detail = {**_serialize_report(report), "content": report.content, "alerts": _alert_items(report)}
    return api_response(data=ReportDetailSerializer(detail).data, message="success")


@extend_schema(
    summary="查看 AI 监控日报详情",
    description="返回指定日报的正文预览内容和告警明细。该接口需要 Bearer JWT 认证。",
    responses={200: ReportDetailSerializer, 404: None, 401: None},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_detail_view(_request, report_id):
    report = MonitorReport.objects.filter(id=report_id).first()
    if report is None:
        return api_response(
            code=404,
            message="日报不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )
    detail = {**_serialize_report(report), "content": report.content, "alerts": _alert_items(report)}
    return api_response(data=ReportDetailSerializer(detail).data, message="success")


@extend_schema(
    summary="下载 AI 监控日报",
    description="下载指定日报的 Word 文档。该接口需要 Bearer JWT 认证。",
    responses={200: OpenApiTypes.BINARY, 404: None, 401: None},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_download_view(_request, report_id):
    report = MonitorReport.objects.filter(id=report_id).first()
    if report is None:
        return api_response(code=404, message="日报不存在", data=None, status=status.HTTP_404_NOT_FOUND)
    if not report.document_path:
        return api_response(code=404, message="日报文档尚未生成", data=None, status=status.HTTP_404_NOT_FOUND)

    path = Path(settings.MEDIA_ROOT) / report.document_path
    if not path.exists():
        return api_response(code=404, message="日报文档文件不存在", data=None, status=status.HTTP_404_NOT_FOUND)

    return FileResponse(
        path.open("rb"),
        as_attachment=True,
        filename=f"monitor-report-{report.report_date.isoformat()}-{report.period_label.replace(':', '')}.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _alert_keyframe_path(alert):
    candidates = [
        alert.snapshot_path,
        getattr(alert.event, "snapshot_path", ""),
    ]
    payload = getattr(alert.event, "payload", {}) or {}
    media = payload.get("media") if isinstance(payload, dict) else {}
    if isinstance(media, dict):
        candidates.extend([media.get("keyframePath"), media.get("keyframeUrl")])
    if isinstance(payload, dict):
        candidates.extend([payload.get("keyframePath"), payload.get("snapshotPath"), payload.get("snapshotUrl")])
    return next((str(value).strip() for value in candidates if value), "")


def _media_url(path):
    if not path:
        return ""
    if str(path).startswith(("http://", "https://", "/")):
        return str(path)
    return f"{settings.MEDIA_URL.rstrip('/')}/{str(path).lstrip('/')}"
