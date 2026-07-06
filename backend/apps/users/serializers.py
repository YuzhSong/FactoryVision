from rest_framework import serializers


class UserPlaceholderSerializer(serializers.Serializer):
    module = serializers.CharField(default="users")
    status = serializers.CharField(default="placeholder")
