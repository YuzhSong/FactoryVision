from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class AuthEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="admin",
            password="password",
            role=User.Role.ADMIN,
        )

    def test_login_returns_jwt_token_and_user_info(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertIn("token", response.data["data"])
        self.assertEqual(response.data["data"]["user"]["username"], "admin")
        self.assertEqual(response.data["data"]["user"]["role"], User.Role.ADMIN)

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], 401)
        self.assertEqual(response.data["message"], "账号或密码错误")

    def test_login_rejects_missing_fields(self):
        response = self.client.post("/api/auth/login/", {}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)
        self.assertIn("username", response.data["data"])
        self.assertIn("password", response.data["data"])

    def test_current_user_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], 401)

    def test_current_user_returns_authenticated_user(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "password"},
            format="json",
        )
        token = login_response.data["data"]["token"]

        response = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["data"]["username"], "admin")
