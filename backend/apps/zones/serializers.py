from rest_framework import serializers

from .models import Zone


class ZonePlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="zones")
    status = serializers.CharField(default="placeholder")


class ZoneListSerializer(serializers.ModelSerializer):
    cameraId = serializers.IntegerField(source="camera_id")
    polygon = serializers.JSONField(source="points")

    class Meta:
        model = Zone
        fields = ("id", "name", "cameraId", "type", "points", "polygon", "enabled", "description")
        read_only_fields = fields
