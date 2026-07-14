from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, extend_schema

from common.response import api_response

from .serializers import AttendancePlaceholderSerializer


@extend_schema(
    summary="考勤模块占位接口",
    description="返回考勤模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: AttendancePlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Attendance placeholder",
            value={
                "code": 200,
                "message": "Attendance module placeholder",
                "data": {"module": "attendance", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    serializer = AttendancePlaceholderSerializer()
    return api_response(data=serializer.data, message="Attendance module placeholder")

# Create your views here.
