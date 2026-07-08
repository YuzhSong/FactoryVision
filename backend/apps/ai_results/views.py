from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, extend_schema

from common.response import api_response

from .serializers import AIResultPlaceholderSerializer, AIResultReportSerializer, HealthCheckSerializer


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
                    "eventIds": [],
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
    return api_response(
        code=200,
        message="AI results accepted",
        data={
            "eventIds": [],
            "alertIds": [],
            "acceptedResults": len(validated["results"]),
            "cameraId": validated["cameraId"],
            "frameId": validated["frameId"],
        },
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

# Create your views here.
