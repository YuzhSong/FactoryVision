from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from common.response import api_response

from .models import Employee
from .serializers import (
    EmployeeCreateSerializer,
    EmployeeListSerializer,
    EmployeePlaceholderSerializer,
)


@api_view(["GET", "POST"])
def employee_root_view(request):
    """
    GET  /api/employees/  → 占位
    POST /api/employees/  → 创建新员工
    """
    if request.method == "GET":
        serializer = EmployeePlaceholderSerializer()
        return api_response(data=serializer.data, message="Employees module placeholder")

    # POST —— 创建员工
    serializer = EmployeeCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee_no = serializer.validated_data["employeeNo"]

    if Employee.objects.filter(employee_no=employee_no).exists():
        return api_response(
            code=409,
            message=f"工号 {employee_no} 已存在",
            data=None,
            status=status.HTTP_409_CONFLICT,
        )

    employee = Employee.objects.create(
        employee_no=employee_no,
        name=serializer.validated_data["name"],
        department=serializer.validated_data.get("department", ""),
        position=serializer.validated_data.get("position", ""),
        phone=serializer.validated_data.get("phone", ""),
    )

    return api_response(
        code=200,
        message="success",
        data={"id": employee.id},
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_list_view(request):
    """
    查询员工列表（分页）。

    GET /api/employees/list/
    参数: page, pageSize, department(可选), status(可选)
    返回: total + items
    """
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("pageSize", 20))
    department = request.query_params.get("department", "")
    emp_status = request.query_params.get("status", "")

    qs = Employee.objects.all()

    if department:
        qs = qs.filter(department=department)
    if emp_status:
        qs = qs.filter(status=emp_status)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = EmployeeListSerializer(qs[start:end], many=True).data

    return api_response(
        code=200,
        message="success",
        data={"total": total, "items": items},
    )
