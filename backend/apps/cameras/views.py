from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import CameraPlaceholderSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = CameraPlaceholderSerializer()
    return api_response(data=serializer.data, message="Cameras module placeholder")

# Create your views here.
