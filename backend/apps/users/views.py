from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from common.response import api_response

from .models import User
from .serializers import (
    LoginSerializer,
    UserPlaceholderSerializer,
    UserSerializer,
)


@api_view(["GET"])
def placeholder_view(_request):
    """保留原占位接口，证明路由存在。"""
    serializer = UserPlaceholderSerializer()
    return api_response(data=serializer.data, message="Users module placeholder")


@api_view(["POST"])
def login_view(request):
    """
    用户登录。

    POST /api/auth/login/
    参数: username, password
    返回: token + 用户信息
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(
        request,
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )

    if user is None:
        return api_response(
            code=401,
            message="账号或密码错误",
            data=None,
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return api_response(
            code=403,
            message="账号已被禁用",
            data=None,
            status=status.HTTP_403_FORBIDDEN,
        )

    refresh = RefreshToken.for_user(user)

    return api_response(
        code=200,
        message="success",
        data={
            "token": str(refresh.access_token),
            "user": UserSerializer(user).data,
        },
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    用户登出。

    POST /api/auth/logout/
    JWT 无状态，前端自行清理 token 即可。
    """
    return api_response(code=200, message="success", data=None)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    获取当前登录用户信息。

    GET /api/auth/me/
    返回: 当前用户信息
    """
    return api_response(
        code=200,
        message="success",
        data=UserSerializer(request.user).data,
    )
