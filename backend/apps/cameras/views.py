import os

import requests
from django.conf import settings
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from common.response import api_response

from .models import Camera
from .serializers import CameraCreateSerializer, CameraListSerializer, CameraPlaceholderSerializer, CameraToggleSerializer, CameraUpdateSerializer
from .stream_config import resolve_stream_start_config

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:9000").rstrip("/")


def _parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _ai_service_headers():
    token = str(getattr(settings, "AI_SERVICE_API_TOKEN", "") or "")
    return {"X-AI-Service-Token": token} if token else {}


def _camera_stream_payload(camera: Camera) -> dict:
    return resolve_stream_start_config(camera)


def _call_ai_service(method: str, path: str, *, json_payload: dict | None = None):
    response = requests.request(
        method=method,
        url=f"{AI_SERVICE_URL}{path}",
        json=json_payload,
        headers=_ai_service_headers(),
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", payload)


@extend_schema(
    summary="摄像头模块占位接口",
    description="返回摄像头模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: CameraPlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Cameras placeholder",
            value={
                "code": 200,
                "message": "Cameras module placeholder",
                "data": {"module": "cameras", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    serializer = CameraPlaceholderSerializer()
    return api_response(data=serializer.data, message="Cameras module placeholder")


@extend_schema(
    summary="查询摄像头列表",
    description="查询摄像头配置，支持关键词搜索（名称/编码/位置）、状态筛选和分页。不传分页参数时返回全量（AI Service 调用兼容）。",
    parameters=[
        OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，正整数"),
        OpenApiParameter("pageSize", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页数量，正整数"),
        OpenApiParameter("keyword", OpenApiTypes.STR, OpenApiParameter.QUERY, description="模糊匹配名称、编码或位置"),
        OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, description="在线状态：online / offline / disabled"),
    ],
    responses={200: CameraListSerializer(many=True)},
    examples=[
        OpenApiExample(
            "摄像头列表响应",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "total": 2,
                    "items": [
                        {
                            "id": 1,
                            "name": "一号车间入口",
                            "code": "CAM001",
                            "streamUrl": "rtmp://srs/live/1",
                            "processedStreamUrl": "rtmp://srs/live/1_detected",
                            "location": "一号车间南侧",
                            "status": "online",
                            "enabled": True,
                        },
                        {
                            "id": 2,
                            "name": "二号车间通道",
                            "code": "CAM002",
                            "streamUrl": "rtmp://srs/live/2",
                            "processedStreamUrl": "",
                            "location": "二号车间东侧",
                            "status": "offline",
                            "enabled": True,
                        },
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
def camera_list_view(request):
    qs = Camera.objects.all()
    keyword = request.query_params.get("keyword", "")
    status_value = request.query_params.get("status")
    enabled_value = request.query_params.get("enabled")

    if keyword:
        qs = qs.filter(
            Q(name__icontains=keyword) | Q(code__icontains=keyword) | Q(location__icontains=keyword)
        )
    if status_value:
        qs = qs.filter(status=status_value)
    if enabled_value is not None:
        qs = qs.filter(enabled=str(enabled_value).lower() in {"1", "true", "yes", "on"})

    total = qs.count()

    page = _parse_positive_int(request.query_params.get("page"))
    page_size = _parse_positive_int(request.query_params.get("pageSize"))
    if page is not None and page_size is not None:
        start = (page - 1) * page_size
        end = start + page_size
        items = CameraListSerializer(qs[start:end], many=True).data
    else:
        items = CameraListSerializer(qs, many=True).data

    return api_response(
        data={"total": total, "items": items},
        message="success",
    )


@extend_schema(
    summary="创建摄像头",
    description="新增摄像头配置。code 编码不填则自动生成 CAM001 格式。该接口需要 Bearer JWT 认证。",
    request=CameraCreateSerializer,
    responses={200: None, 400: None, 409: None},
    examples=[
        OpenApiExample(
            "创建请求",
            value={"name": "一号车间入口", "code": "CAM001", "streamUrl": "rtmp://srs/live/1", "processedStreamUrl": "rtmp://srs/live/1_detected", "location": "南侧"},
            request_only=True,
        ),
        OpenApiExample(
            "创建成功",
            value={"code": 200, "message": "success", "data": {"id": 1, "code": "CAM001"}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "编码重复",
            value={"code": 409, "message": "编码 CAM001 已存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["409"],
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camera_create_view(request):
    """
    创建新摄像头。

    POST /api/cameras/
    参数: name(必填), code(可选,自动生成), streamUrl(必填), processedStreamUrl(可选), location(可选)
    返回: id + code
    """
    serializer = CameraCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    validated = serializer.validated_data
    code = validated.get("code", "") or ""

    if code and Camera.objects.filter(code=code).exists():
        return api_response(
            code=409,
            message=f"编码 {code} 已存在",
            data=None,
            status=status.HTTP_409_CONFLICT,
        )

    camera = Camera.objects.create(
        name=validated["name"],
        code=code,
        stream_url=validated["streamUrl"],
        processed_stream_url=validated.get("processedStreamUrl", ""),
        location=validated.get("location", ""),
        include_faces=validated.get("includeFaces", False),
    )

    if not camera.code:
        camera.code = f"CAM{camera.id:03d}"
        camera.save(update_fields=["code"])

    return api_response(
        code=200,
        message="success",
        data={"id": camera.id, "code": camera.code},
    )


@extend_schema(
    summary="编辑摄像头",
    description="编辑摄像头配置，所有字段可选，不传则保持原值。该接口需要 Bearer JWT 认证。",
    request=CameraUpdateSerializer,
    responses={200: None, 400: None, 404: None, 409: None},
    examples=[
        OpenApiExample(
            "编辑请求",
            value={"name": "一号车间入口（更新）", "location": "南侧门"},
            request_only=True,
        ),
        OpenApiExample(
            "编辑成功",
            value={"code": 200, "message": "success", "data": {"id": 1, "code": "CAM001"}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "摄像头不存在",
            value={"code": 404, "message": "摄像头不存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def camera_update_view(request, camera_id):
    """
    编辑摄像头。

    PUT /api/cameras/{id}/
    所有字段可选，不传的保持原值。
    """
    try:
        camera = Camera.objects.get(id=camera_id)
    except Camera.DoesNotExist:
        return api_response(
            code=404,
            message="摄像头不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CameraUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    validated = serializer.validated_data

    if "code" in validated:
        new_code = validated["code"]
        if Camera.objects.filter(code=new_code).exclude(id=camera_id).exists():
            return api_response(
                code=409,
                message=f"编码 {new_code} 已存在",
                data=None,
                status=status.HTTP_409_CONFLICT,
            )
        camera.code = new_code
    if "name" in validated:
        camera.name = validated["name"]
    if "streamUrl" in validated:
        camera.stream_url = validated["streamUrl"]
    if "processedStreamUrl" in validated:
        camera.processed_stream_url = validated["processedStreamUrl"]
    if "location" in validated:
        camera.location = validated["location"]
    if "enabled" in validated:
        camera.enabled = validated["enabled"]
    if "includeFaces" in validated:
        camera.include_faces = validated["includeFaces"]

    camera.save()

    return api_response(
        code=200,
        message="success",
        data={"id": camera.id, "code": camera.code},
    )


@extend_schema(
    summary="切换摄像头状态",
    description="切换摄像头的在线/离线/停用状态。该接口需要 Bearer JWT 认证。",
    request=CameraToggleSerializer,
    responses={200: None, 400: None, 404: None},
    examples=[
        OpenApiExample(
            "切换请求",
            value={"status": "online"},
            request_only=True,
        ),
        OpenApiExample(
            "切换成功",
            value={"code": 200, "message": "success", "data": {"id": 1, "status": "online"}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "摄像头不存在",
            value={"code": 404, "message": "摄像头不存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camera_toggle_view(request, camera_id):
    """
    切换摄像头状态。

    POST /api/cameras/{id}/toggle/
    参数: status (online/offline/disabled)
    """
    try:
        camera = Camera.objects.get(id=camera_id)
    except Camera.DoesNotExist:
        return api_response(
            code=404,
            message="摄像头不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = CameraToggleSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    camera.status = serializer.validated_data["status"]
    camera.save(update_fields=["status", "updated_at"])

    return api_response(
        code=200,
        message="success",
        data={"id": camera.id, "status": camera.status},
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def camera_stream_status_view(_request, camera_id):
    try:
        camera = Camera.objects.get(id=camera_id)
    except Camera.DoesNotExist:
        return api_response(
            code=404,
            message="鎽勫儚澶翠笉瀛樺湪",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        data = _call_ai_service("GET", "/streams/status")
    except requests.RequestException as exc:
        return api_response(
            code=502,
            message=f"AI Service unavailable: {exc}",
            data={"cameraId": camera.id, "running": False},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    data["cameraConfig"] = _camera_stream_payload(camera)
    return api_response(code=200, message="success", data=data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camera_stream_start_view(_request, camera_id):
    try:
        camera = Camera.objects.get(id=camera_id)
    except Camera.DoesNotExist:
        return api_response(
            code=404,
            message="鎽勫儚澶翠笉瀛樺湪",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    payload = _camera_stream_payload(camera)
    if not payload["inputUrl"]:
        return api_response(
            code=422,
            message="Camera inputUrl is required",
            data=None,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if not payload["outputUrl"]:
        return api_response(
            code=422,
            message="Unable to derive processed outputUrl for camera",
            data=payload,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if not payload["playUrl"]:
        return api_response(
            code=422,
            message="Unable to derive processed playUrl for camera",
            data=payload,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        data = _call_ai_service("POST", "/streams/start", json_payload=payload)
    except requests.RequestException as exc:
        return api_response(
            code=502,
            message=f"AI Service unavailable: {exc}",
            data=payload,
            status=status.HTTP_502_BAD_GATEWAY,
        )

    data["cameraConfig"] = payload
    return api_response(code=200, message="success", data=data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def camera_stream_stop_view(_request, camera_id):
    try:
        Camera.objects.get(id=camera_id)
    except Camera.DoesNotExist:
        return api_response(
            code=404,
            message="鎽勫儚澶翠笉瀛樺湪",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        data = _call_ai_service("POST", "/streams/stop")
    except requests.RequestException as exc:
        return api_response(
            code=502,
            message=f"AI Service unavailable: {exc}",
            data={"cameraId": camera_id, "running": False},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    return api_response(code=200, message="success", data=data)
