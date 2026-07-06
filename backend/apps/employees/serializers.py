from rest_framework import serializers


class EmployeePlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="employees")
    status = serializers.CharField(default="placeholder")
