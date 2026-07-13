from rest_framework import serializers


class ReportListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reportDate = serializers.DateField()
    alertCount = serializers.IntegerField()
    highAlertCount = serializers.IntegerField()
    pendingAlertCount = serializers.IntegerField()
    status = serializers.CharField()
    aiSummary = serializers.CharField()
    documentPath = serializers.CharField()
    generatedAt = serializers.DateTimeField(allow_null=True)


class ReportDetailSerializer(ReportListItemSerializer):
    content = serializers.CharField()
    alerts = serializers.ListField(child=serializers.DictField())
