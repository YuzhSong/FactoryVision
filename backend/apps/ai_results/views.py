from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import AIResultPlaceholderSerializer, AIResultReportSerializer, HealthCheckSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = AIResultPlaceholderSerializer()
    return api_response(data=serializer.data, message="AI results module placeholder")


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


@api_view(["GET"])
def health_check(_request):
    serializer = HealthCheckSerializer()
    return api_response(data=serializer.data, message="Backend service is healthy")

# Create your views here.
