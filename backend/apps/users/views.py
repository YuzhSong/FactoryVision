from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import UserPlaceholderSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = UserPlaceholderSerializer()
    return api_response(data=serializer.data, message="Users module placeholder")

# Create your views here.
