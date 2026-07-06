from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import ZonePlaceholderSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = ZonePlaceholderSerializer()
    return api_response(data=serializer.data, message="Zones module placeholder")

# Create your views here.
