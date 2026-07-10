from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from apps.cameras.models import Camera
from common.response import api_response

from .models import Zone
from .serializers import ZoneCreateSerializer, ZoneListSerializer, ZonePlaceholderSerializer


@extend_schema(
    summary="区域模块占位接口",
    description="返回区域模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: ZonePlaceholderSerializer},
    examples=[
        OpenApiExample(
            "区域模块占位",
            value={
                "code": 200,
                "message": "Zones module placeholder",
                "data": {"module": "zones", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    serializer = ZonePlaceholderSerializer()
    return api_response(data=serializer.data, message="Zones module placeholder")


@extend_schema(
    summary="查询警戒区域列表",
    description="查询指定摄像头的警戒区域配置。选择摄像头后返回对应的多边形区域列表。",
    parameters=[
        OpenApiParameter("cameraId", OpenApiTypes.STR, OpenApiParameter.QUERY, description="摄像头 ID 或编码"),
        OpenApiParameter("enabled", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="是否启用"),
    ],
    responses={200: ZoneListSerializer(many=True)},
    examples=[
        OpenApiExample(
            "区域列表响应",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "total": 1,
                    "items": [
                        {
                            "id": 1,
                            "name": "危险设备区",
                            "cameraId": 1,
                            "type": "danger",
                            "points": [
                                {"x": 0.56, "y": 0.45},
                                {"x": 0.82, "y": 0.43},
                                {"x": 0.87, "y": 0.72},
                            ],
                            "enabled": True,
                            "description": "设备运行危险区域",
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
def zone_list_view(request):
    qs = Zone.objects.select_related("camera").all()
    camera_id = request.query_params.get("cameraId")
    enabled_value = request.query_params.get("enabled")

    if camera_id:
        if str(camera_id).isdigit():
            qs = qs.filter(camera_id=int(camera_id))
        else:
            qs = qs.filter(camera__code=camera_id)
    if enabled_value is not None:
        qs = qs.filter(enabled=str(enabled_value).lower() in {"1", "true", "yes", "on"})

    return api_response(
        data={"total": qs.count(), "items": ZoneListSerializer(qs, many=True).data},
        message="success",
    )


@extend_schema(
    summary="创建警戒区域",
    description="为指定摄像头创建多边形警戒区域。点位少于 3 个时拒绝创建。该接口需要 Bearer JWT 认证。",
    request=ZoneCreateSerializer,
    responses={200: None, 400: None, 422: None},
    examples=[
        OpenApiExample(
            "创建请求",
            value={
                "cameraId": 1,
                "name": "危险设备区",
                "type": "danger",
                "points": [
                    {"x": 0.56, "y": 0.45},
                    {"x": 0.82, "y": 0.43},
                    {"x": 0.87, "y": 0.72},
                ],
                "enabled": True,
                "description": "设备运行危险区域",
            },
            request_only=True,
        ),
        OpenApiExample(
            "创建成功",
            value={"code": 200, "message": "success", "data": {"id": 1}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "点位不足",
            value={"code": 422, "message": "多边形至少需要 3 个顶点", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["422"],
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def zone_create_view(request):
    """
    创建警戒区域。

    POST /api/zones/
    参数: cameraId, name, type(可选), points, enabled(可选), description(可选)
    返回: id
    """
    serializer = ZoneCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400 if "points" not in serializer.errors else 422,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    validated = serializer.validated_data

    try:
        camera = Camera.objects.get(id=validated["cameraId"])
    except Camera.DoesNotExist:
        return api_response(
            code=404,
            message="摄像头不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    zone = Zone.objects.create(
        camera=camera,
        name=validated["name"],
        type=validated.get("type", "restricted"),
        points=validated["points"],
        enabled=validated.get("enabled", True),
        description=validated.get("description", ""),
    )

    return api_response(
        code=200,
        message="success",
        data={"id": zone.id},
    )
