from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User

from .models import Employee


class EmployeeEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="admin",
            password="password",
            role=User.Role.ADMIN,
        )

    def authenticate(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "admin", "password": "password"},
            format="json",
        )
        token = login_response.data["data"]["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_create_employee_returns_new_id(self):
        response = self.client.post(
            "/api/employees/",
            {
                "employeeNo": "E001",
                "name": "张三",
                "department": "生产部",
                "position": "操作员",
                "phone": "13800000000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertIsNotNone(response.data["data"]["id"])
        self.assertTrue(Employee.objects.filter(employee_no="E001").exists())

    def test_create_employee_rejects_duplicate_employee_no(self):
        Employee.objects.create(employee_no="E001", name="张三")

        response = self.client.post(
            "/api/employees/",
            {"employeeNo": "E001", "name": "李四"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], 409)

    def test_employee_list_requires_authentication(self):
        response = self.client.get("/api/employees/list/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], 401)

    def test_employee_list_filters_and_paginates(self):
        Employee.objects.create(
            employee_no="E001",
            name="张三",
            department="生产部",
            position="操作员",
            phone="13800000000",
        )
        Employee.objects.create(
            employee_no="E002",
            name="李四",
            department="仓储部",
            position="管理员",
        )
        self.authenticate()

        response = self.client.get(
            "/api/employees/list/?page=1&pageSize=20&department=生产部"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        self.assertEqual(response.data["data"]["total"], 1)
        self.assertEqual(response.data["data"]["items"][0]["employeeNo"], "E001")
        self.assertEqual(response.data["data"]["items"][0]["position"], "操作员")

    def test_employee_list_rejects_invalid_pagination(self):
        self.authenticate()

        response = self.client.get("/api/employees/list/?page=abc&pageSize=0")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], 400)
