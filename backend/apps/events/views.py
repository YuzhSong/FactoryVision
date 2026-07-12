from rest_framework.decorators import api_view
from drf_spectacular.utils import OpenApiExample, extend_schema

from common.response import api_response

from .models import Event
from .serializers import EventListSerializer, EventPlaceholderSerializer


@extend_schema(
    summary="事件模块占位接口",
    description="返回事件模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: EventPlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Events placeholder",
            value={
                "code": 200,
                "message": "Events module placeholder",
                "data": {"module": "events", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    serializer = EventPlaceholderSerializer()
    return api_response(data=serializer.data, message="Events module placeholder")


@extend_schema(
    summary="List formal events",
    description="Return formal Event records without any AIEvent compatibility data.",
    responses={200: EventListSerializer(many=True)},
)
@api_view(["GET"])
def event_list_view(request):
    events = Event.objects.select_related("camera").all()
    camera_id = request.query_params.get("cameraId")
    if camera_id:
        events = events.filter(camera_id=camera_id)
    return api_response(
        data={"total": events.count(), "items": EventListSerializer(events, many=True).data},
        message="success",
    )

# Create your views here.
