from rest_framework import serializers


class AIResultPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="ai_results")
    status = serializers.CharField(default="placeholder")


class AIResultReportSerializer(serializers.Serializer):
    cameraId = serializers.IntegerField(min_value=1)
    frameId = serializers.CharField()
    timestamp = serializers.DateTimeField()
    results = serializers.ListField(child=serializers.DictField(), allow_empty=True)


class HealthCheckSerializer(serializers.Serializer):
    service = serializers.CharField(default="backend")
    status = serializers.CharField(default="ok")
    stage = serializers.CharField(default="skeleton")
