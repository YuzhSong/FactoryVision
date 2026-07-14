from rest_framework import serializers

from .models import User


class UserPlaceholderSerializer(serializers.Serializer):
    """保留原占位序列化器，供占位接口使用。"""

    module = serializers.CharField(default="users")
    status = serializers.CharField(default="placeholder")


class LoginSerializer(serializers.Serializer):
    """登录请求参数校验。"""

    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(required=True, max_length=128)


class UserSerializer(serializers.ModelSerializer):
    """用户信息输出。"""

    class Meta:
        model = User
        fields = ("id", "username", "role")
        read_only_fields = fields
