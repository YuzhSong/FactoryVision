from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from common.response import api_response

from .models import Camera
from .serializers import CameraListSerializer, CameraPlaceholderSerializer


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
    summary="List cameras",
    description="Return camera configs for ai-service bootstrap and frontend reuse.",
    parameters=[
        OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, description="online/offline/disabled"),
        OpenApiParameter("enabled", OpenApiTypes.BOOL, OpenApiParameter.QUERY, description="Filter enabled cameras"),
    ],
    responses={200: CameraListSerializer(many=True)},
)
@api_view(["GET"])
def camera_list_view(request):
    qs = Camera.objects.all()
    status_value = request.query_params.get("status")
    enabled_value = request.query_params.get("enabled")

    if status_value:
        qs = qs.filter(status=status_value)
    if enabled_value is not None:
        qs = qs.filter(enabled=str(enabled_value).lower() in {"1", "true", "yes", "on"})

    return api_response(
        data={"total": qs.count(), "items": CameraListSerializer(qs, many=True).data},
        message="success",
    )
