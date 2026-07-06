from rest_framework import serializers


class ZonePlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="zones")
    status = serializers.CharField(default="placeholder")
