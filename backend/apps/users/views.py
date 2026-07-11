from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import OpenApiExample, extend_schema

from common.response import api_response

from .models import User
from .serializers import (
    LoginSerializer,
    UserPlaceholderSerializer,
    UserSerializer,
)


@extend_schema(
    summary="用户模块占位接口",
    description="返回用户模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: UserPlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Users placeholder",
            value={
                "code": 200,
                "message": "Users module placeholder",
                "data": {"module": "users", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def placeholder_view(_request):
    """保留原占位接口，证明路由存在。"""
    serializer = UserPlaceholderSerializer()
    return api_response(data=serializer.data, message="Users module placeholder")


@extend_schema(
    summary="用户登录",
    description="使用用户名和密码登录。认证成功后返回 Bearer JWT token 和用户信息。",
    request=LoginSerializer,
    responses={
        200: None,
        400: None,
        401: None,
        403: None,
    },
    examples=[
        OpenApiExample(
            "Login request",
            value={"username": "admin", "password": "password"},
            request_only=True,
        ),
        OpenApiExample(
            "Login success",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "token": "jwt-access-token",
                    "user": {"id": 1, "username": "admin", "role": "admin"},
                },
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Invalid credentials",
            value={
                "code": 401,
                "message": "账号或密码错误",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["401"],
        ),
    ],
)
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


@extend_schema(
    summary="用户登出",
    description="JWT 无状态登出接口。后端返回成功，前端负责清理本地 token。该接口需要 Bearer JWT 认证。",
    request=None,
    responses={
        200: None,
        401: None,
    },
    examples=[
        OpenApiExample(
            "Logout success",
            value={
                "code": 200,
                "message": "success",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
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


@extend_schema(
    summary="获取当前用户",
    description="返回当前 Bearer JWT 对应的用户信息。该接口需要 Bearer JWT 认证。",
    responses={
        200: UserSerializer,
        401: None,
    },
    examples=[
        OpenApiExample(
            "Current user",
            value={
                "code": 200,
                "message": "success",
                "data": {"id": 1, "username": "admin", "role": "admin"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
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
