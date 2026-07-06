from rest_framework import serializers


class CameraPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="cameras")
    status = serializers.CharField(default="placeholder")
