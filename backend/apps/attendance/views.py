from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import AttendancePlaceholderSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = AttendancePlaceholderSerializer()
    return api_response(data=serializer.data, message="Attendance module placeholder")

# Create your views here.
