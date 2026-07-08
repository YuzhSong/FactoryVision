from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, extend_schema

from common.response import api_response

from .serializers import CameraPlaceholderSerializer


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

# Create your views here.
