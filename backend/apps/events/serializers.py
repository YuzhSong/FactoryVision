from rest_framework import serializers

from .models import Event


class EventPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="events")
    status = serializers.CharField(default="placeholder")


class EventListSerializer(serializers.ModelSerializer):
    cameraId = serializers.IntegerField(source="camera_id", allow_null=True)
    cameraIdentifier = serializers.CharField(source="camera_identifier")
    frameId = serializers.CharField(source="frame_id")
    trackId = serializers.CharField(source="track_id")
    snapshotPath = serializers.CharField(source="snapshot_path")

    class Meta:
        model = Event
        fields = (
            "id",
            "cameraId",
            "cameraIdentifier",
            "event_type",
            "source",
            "severity",
            "status",
            "occurred_at",
            "frameId",
            "trackId",
            "bbox",
            "confidence",
            "snapshotPath",
            "payload",
        )
        read_only_fields = fields
