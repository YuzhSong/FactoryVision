from django.db import models
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema

from common.response import api_response

from .models import Employee
from .serializers import (
    EmployeeCreateSerializer,
    EmployeeListSerializer,
    EmployeePlaceholderSerializer,
)


def _parse_positive_int(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


@extend_schema(
    methods=["GET"],
    summary="员工模块占位接口",
    description="返回员工模块当前占位状态，用于确认路由和模块边界存在。",
    responses={200: EmployeePlaceholderSerializer},
    examples=[
        OpenApiExample(
            "Employees placeholder",
            value={
                "code": 200,
                "message": "Employees module placeholder",
                "data": {"module": "employees", "status": "placeholder"},
                "requestId": "uuid",
            },
            response_only=True,
        ),
    ],
)
@extend_schema(
    methods=["POST"],
    summary="创建员工",
    description="新增员工档案。工号重复时返回 409。",
    request=EmployeeCreateSerializer,
    responses={
        200: None,
        400: None,
        409: None,
    },
    examples=[
        OpenApiExample(
            "Create employee request",
            value={
                "employeeNo": "E001",
                "name": "张三",
                "department": "生产部",
                "position": "操作员",
                "phone": "13800000000",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Create employee response",
            value={
                "code": 200,
                "message": "success",
                "data": {"id": 1},
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Duplicate employeeNo",
            value={
                "code": 409,
                "message": "工号 E001 已存在",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["409"],
        ),
    ],
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


@extend_schema(
    summary="查询员工列表",
    description="查询员工档案列表，支持按关键词模糊匹配姓名或工号。该接口需要 Bearer JWT 认证。",
    parameters=[
        OpenApiParameter("page", OpenApiTypes.INT, OpenApiParameter.QUERY, description="页码，正整数，默认 1"),
        OpenApiParameter("pageSize", OpenApiTypes.INT, OpenApiParameter.QUERY, description="每页数量，正整数，默认 20"),
        OpenApiParameter("keyword", OpenApiTypes.STR, OpenApiParameter.QUERY, description="关键词，模糊匹配姓名或工号，可选"),
        OpenApiParameter("department", OpenApiTypes.STR, OpenApiParameter.QUERY, description="部门筛选，可选"),
        OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, description="员工状态，可选：active/inactive"),
    ],
    responses={
        200: EmployeeListSerializer(many=True),
        400: None,
        401: None,
    },
    examples=[
        OpenApiExample(
            "Employee list response",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "total": 1,
                    "items": [
                        {
                            "id": 1,
                            "employeeNo": "E001",
                            "name": "张三",
                            "department": "生产部",
                            "position": "操作员",
                            "phone": "13800000000",
                            "status": "active",
                        }
                    ],
                },
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Invalid pagination",
            value={
                "code": 400,
                "message": "分页参数必须为正整数",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["400"],
        ),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_list_view(request):
    """
    查询员工列表（分页）。

    GET /api/employees/list/
    参数: page, pageSize, keyword(可选), department(可选), status(可选)
    返回: total + items
    """
    page = _parse_positive_int(request.query_params.get("page", 1))
    page_size = _parse_positive_int(request.query_params.get("pageSize", 20))
    if page is None or page_size is None:
        return api_response(
            code=400,
            message="分页参数必须为正整数",
            data=None,
            status=status.HTTP_400_BAD_REQUEST,
        )

    keyword = request.query_params.get("keyword", "")
    department = request.query_params.get("department", "")
    emp_status = request.query_params.get("status", "")

    qs = Employee.objects.all()

    if keyword:
        qs = qs.filter(
            models.Q(name__icontains=keyword) | models.Q(employee_no__icontains=keyword)
        )
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
