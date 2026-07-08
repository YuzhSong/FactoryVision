from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from common.response import api_response

from .models import Zone
from .serializers import ZoneListSerializer, ZonePlaceholderSerializer


@extend_schema(
    summary="区域模块占位接口",
    description="返回区域模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: ZonePlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Zones placeholder",
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
    summary="List zones",
    description="Return detection zones for ai-service bootstrap and rule checks.",
    parameters=[
        OpenApiParameter("cameraId", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Camera id or code"),
        OpenApiParameter("enabled", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="Filter enabled zones"),
    ],
    responses={200: ZoneListSerializer(many=True)},
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
