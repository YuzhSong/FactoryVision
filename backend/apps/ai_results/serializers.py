from rest_framework import serializers

from .models import Alert


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


class AlertSerializer(serializers.ModelSerializer):
    eventType = serializers.CharField(source="event.event_type")
    severity = serializers.CharField(source="event.severity")
    cameraId = serializers.IntegerField(source="camera_id", allow_null=True)
    cameraName = serializers.CharField(source="camera.name", allow_null=True)
    occurredAt = serializers.DateTimeField(source="event.occurred_at")

    class Meta:
        model = Alert
        fields = (
            "id",
            "title",
            "eventType",
            "severity",
            "status",
            "cameraId",
            "cameraName",
            "occurredAt",
            "description",
        )
        read_only_fields = fields


class AlertHandleSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Alert.Status.choices)


class EventTrendSerializer(serializers.Serializer):
    hour = serializers.DateTimeField()
    count = serializers.IntegerField()


class DashboardSummarySerializer(serializers.Serializer):
    cameraCount = serializers.IntegerField()
    onlineCameraCount = serializers.IntegerField()
    employeeCount = serializers.IntegerField()
    todayEventCount = serializers.IntegerField()
    todayAlertCount = serializers.IntegerField()
    pendingAlertCount = serializers.IntegerField()
    recentAlerts = AlertSerializer(many=True)
    eventTrend = EventTrendSerializer(many=True)
