from rest_framework import serializers


class AIResultPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="ai_results")
    status = serializers.CharField(default="placeholder")


class HealthCheckSerializer(serializers.Serializer):
    service = serializers.CharField(default="backend")
    status = serializers.CharField(default="ok")
    stage = serializers.CharField(default="skeleton")
