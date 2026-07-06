from rest_framework.decorators import api_view

from common.response import api_response

from .serializers import EmployeePlaceholderSerializer


@api_view(["GET"])
def placeholder_view(_request):
    serializer = EmployeePlaceholderSerializer()
    return api_response(data=serializer.data, message="Employees module placeholder")

# Create your views here.
