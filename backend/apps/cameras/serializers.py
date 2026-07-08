from rest_framework import serializers

from .models import Camera


class CameraPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="cameras")
    status = serializers.CharField(default="placeholder")


class CameraListSerializer(serializers.ModelSerializer):
    cameraId = serializers.CharField(source="code")
    streamUrl = serializers.CharField(source="stream_url")
    processedStreamUrl = serializers.CharField(source="processed_stream_url")

    class Meta:
        model = Camera
        fields = (
            "id",
            "name",
            "code",
            "cameraId",
            "streamUrl",
            "processedStreamUrl",
            "location",
            "status",
            "enabled",
        )
        read_only_fields = fields
