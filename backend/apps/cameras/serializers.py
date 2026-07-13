from rest_framework import serializers

from .models import Camera


class CameraPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="cameras")
    status = serializers.CharField(default="placeholder")


class CameraCreateSerializer(serializers.Serializer):
    """创建摄像头——参数校验。"""

    name = serializers.CharField(required=True, max_length=128)
    code = serializers.CharField(required=False, max_length=64, default="")
    streamUrl = serializers.CharField(required=True, max_length=512)
    processedStreamUrl = serializers.CharField(required=False, max_length=512, default="")
    location = serializers.CharField(required=False, max_length=255, default="")
    includeFaces = serializers.BooleanField(required=False, default=False)


class CameraUpdateSerializer(serializers.Serializer):
    """编辑摄像头——所有字段可选，不传保持原值。"""

    name = serializers.CharField(required=False, max_length=128)
    code = serializers.CharField(required=False, max_length=64)
    streamUrl = serializers.CharField(required=False, max_length=512)
    processedStreamUrl = serializers.CharField(required=False, max_length=512)
    location = serializers.CharField(required=False, max_length=255)
    enabled = serializers.BooleanField(required=False)
    includeFaces = serializers.BooleanField(required=False)


class CameraToggleSerializer(serializers.Serializer):
    """切换摄像头状态。"""

    status = serializers.ChoiceField(choices=["online", "offline", "disabled"])


class CameraListSerializer(serializers.ModelSerializer):
    cameraId = serializers.CharField(source="code")
    streamUrl = serializers.CharField(source="stream_url")
    processedStreamUrl = serializers.CharField(source="processed_stream_url")
    includeFaces = serializers.BooleanField(source="include_faces")
    streamConfig = serializers.SerializerMethodField()

    def get_streamConfig(self, camera):
        from .stream_config import resolve_stream_start_config

        return resolve_stream_start_config(camera)

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
            "includeFaces",
            "streamConfig",
        )
        read_only_fields = fields
