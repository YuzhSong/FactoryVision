from rest_framework import serializers


class AttendancePlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="attendance")
    status = serializers.CharField(default="placeholder")
