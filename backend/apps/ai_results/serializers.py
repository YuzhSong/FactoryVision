from rest_framework import serializers


class AIResultPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="ai_results")
    status = serializers.CharField(default="placeholder")


class AIResultReportSerializer(serializers.Serializer):
    cameraId = serializers.CharField()
    frameId = serializers.CharField(required=False, allow_blank=True, default="")
    timestamp = serializers.DateTimeField()
    results = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    eventMedia = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class HealthCheckSerializer(serializers.Serializer):
    service = serializers.CharField(default="backend")
    status = serializers.CharField(default="ok")
    stage = serializers.CharField(default="skeleton")
