from rest_framework import serializers


class EventPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="events")
    status = serializers.CharField(default="placeholder")
