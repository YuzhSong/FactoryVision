from django.urls import path

from .views import current_user_view, login_view, logout_view, placeholder_view

urlpatterns = [
    # 原占位接口
    path("", placeholder_view, name="users-placeholder"),
    # Auth 接口
    path("login/", login_view, name="auth-login"),
    path("logout/", logout_view, name="auth-logout"),
    path("me/", current_user_view, name="auth-me"),
]
