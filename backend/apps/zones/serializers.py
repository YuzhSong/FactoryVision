from rest_framework import serializers

from .models import Zone


class ZonePlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="zones")
    status = serializers.CharField(default="placeholder")


class ZoneCreateSerializer(serializers.Serializer):
    """创建警戒区域——参数校验。"""

    cameraId = serializers.IntegerField(required=True, min_value=1)
    name = serializers.CharField(required=True, max_length=128)
    type = serializers.ChoiceField(required=False, choices=["restricted", "danger", "workstation", "general"])
    points = serializers.ListField(required=True)
    enabled = serializers.BooleanField(required=False, default=True)
    description = serializers.CharField(required=False, max_length=512, default="")

    def validate_points(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("多边形至少需要 3 个顶点")
        return value


class ZoneListSerializer(serializers.ModelSerializer):
    cameraId = serializers.IntegerField(source="camera_id")
    polygon = serializers.JSONField(source="points", read_only=True)

    class Meta:
        model = Zone
        fields = ("id", "name", "cameraId", "type", "points", "polygon", "enabled", "description")
        read_only_fields = fields
