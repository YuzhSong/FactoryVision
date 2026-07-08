from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, extend_schema

from common.response import api_response

from .serializers import ZonePlaceholderSerializer


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

# Create your views here.
