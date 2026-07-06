from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import AIResultPlaceholderSerializer, HealthCheckSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = AIResultPlaceholderSerializer()
    return api_response(data=serializer.data, message="AI results module placeholder")


@api_view(["GET"])
def health_check(_request):
    serializer = HealthCheckSerializer()
    return api_response(data=serializer.data, message="Backend service is healthy")

# Create your views here.
