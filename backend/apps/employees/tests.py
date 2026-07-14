from django.test import TestCase
from rest_framework.test import APIClient
from unittest import mock

from apps.face.models import FaceFeature
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
        self.authenticate()
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
        self.authenticate()

        response = self.client.post(
            "/api/employees/",
            {"employeeNo": "E001", "name": "李四"},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], 409)

    def test_create_employee_requires_authentication(self):
        response = self.client.post(
            "/api/employees/",
            {"employeeNo": "E001", "name": "张三"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

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

    def test_update_employee_persists_fields(self):
        employee = Employee.objects.create(
            employee_no="E010",
            name="Alice",
            department="Production",
            position="Operator",
            phone="10086",
        )
        self.authenticate()

        response = self.client.put(
            f"/api/employees/{employee.id}/",
            {
                "employeeNo": "E011",
                "name": "Alice Updated",
                "department": "Safety",
                "position": "Supervisor",
                "phone": "10010",
                "status": "inactive",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], 200)
        employee.refresh_from_db()
        self.assertEqual(employee.employee_no, "E011")
        self.assertEqual(employee.name, "Alice Updated")
        self.assertEqual(employee.department, "Safety")
        self.assertEqual(employee.position, "Supervisor")
        self.assertEqual(employee.phone, "10010")
        self.assertEqual(employee.status, Employee.Status.INACTIVE)

    def test_delete_employee_cascades_face_features_and_notifies_ai_cache(self):
        employee = Employee.objects.create(employee_no="E020", name="Li Si")
        FaceFeature.objects.create(
            employee=employee,
            face_type=FaceFeature.FaceType.FRONT,
            feature_vector=[0.0] * 512,
            image_path="faces/1/front.jpg",
        )
        self.authenticate()

        with mock.patch("apps.employees.views.requests.post") as post:
            response = self.client.delete(f"/api/employees/{employee.id}/delete/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Employee.objects.filter(id=employee.id).exists())
        self.assertFalse(FaceFeature.objects.filter(employee_id=employee.id).exists())
        post.assert_called_once()
        self.assertTrue(post.call_args.args[0].endswith("/cache/employees/delete"))
        self.assertEqual(post.call_args.kwargs["json"], {"employeeIds": [employee.id]})
