import os
import requests
import shutil
from pathlib import Path

from django.conf import settings
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
    EmployeeUpdateSerializer,
)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:9000")


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
@permission_classes([IsAuthenticated])
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


@extend_schema(
    summary="编辑员工",
    description="编辑员工档案，所有字段可选。修改成功通知 AI Service 刷新人脸库。该接口需要 Bearer JWT 认证。",
    request=EmployeeUpdateSerializer,
    responses={200: None, 400: None, 404: None, 409: None},
    examples=[
        OpenApiExample(
            "编辑请求",
            value={"name": "张三（更新）", "department": "质检部"},
            request_only=True,
        ),
        OpenApiExample(
            "编辑成功",
            value={"code": 200, "message": "success", "data": {"id": 1}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "员工不存在",
            value={"code": 404, "message": "员工不存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def employee_update_view(request, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return api_response(
            code=404,
            message="员工不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = EmployeeUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    validated = serializer.validated_data
    if "employeeNo" in validated:
        new_no = validated["employeeNo"]
        if Employee.objects.filter(employee_no=new_no).exclude(id=employee_id).exists():
            return api_response(
                code=409,
                message=f"工号 {new_no} 已存在",
                data=None,
                status=status.HTTP_409_CONFLICT,
            )
        employee.employee_no = new_no
    if "name" in validated:
        employee.name = validated["name"]
    if "department" in validated:
        employee.department = validated["department"]
    if "position" in validated:
        employee.position = validated["position"]
    if "phone" in validated:
        employee.phone = validated["phone"]
    if "status" in validated:
        employee.status = validated["status"]

    employee.save()

    _notify_ai_cache("employees/upsert", {"employees": [{"id": employee.id, "name": employee.name, "employeeNo": employee.employee_no}]})

    return api_response(
        code=200,
        message="success",
        data={"id": employee.id},
    )


@extend_schema(
    summary="删除员工",
    description="删除员工档案，级联删除人脸特征和本地图片，通知 AI Service。该接口需要 Bearer JWT 认证。",
    responses={200: None, 404: None},
    examples=[
        OpenApiExample(
            "删除成功",
            value={"code": 200, "message": "success", "data": {"id": 1}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "员工不存在",
            value={"code": 404, "message": "员工不存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def employee_delete_view(request, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return api_response(
            code=404,
            message="员工不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    eid = employee.id
    employee.delete()

    face_dir = Path(settings.BASE_DIR) / "media" / "faces" / str(eid)
    if face_dir.exists():
        shutil.rmtree(face_dir, ignore_errors=True)

    _notify_ai_cache("employees/delete", {"employeeIds": [eid]})

    return api_response(
        code=200,
        message="success",
        data={"id": eid},
    )


@extend_schema(
    summary="查询员工人脸列表",
    description="返回指定员工的所有已录入人脸特征记录。该接口需要 Bearer JWT 认证。",
    responses={200: None, 404: None},
    examples=[
        OpenApiExample(
            "人脸列表",
            value={
                "code": 200,
                "message": "success",
                "data": [
                    {"id": 1, "faceType": "front", "imagePath": "faces/3/3_front_abc.jpg", "createdAt": "2026-07-12T10:00:00+08:00"},
                    {"id": 2, "faceType": "left", "imagePath": "faces/3/3_left_abc.jpg", "createdAt": "2026-07-12T10:00:01+08:00"},
                ],
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_face_list_view(request, employee_id):
    if not Employee.objects.filter(id=employee_id).exists():
        return api_response(
            code=404,
            message="员工不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    faces = Employee.objects.get(id=employee_id).face_features.all()
    items = [
        {
            "id": f.id,
            "faceType": f.face_type,
            "imageUrl": request.build_absolute_uri(settings.MEDIA_URL + f.image_path.replace("\\", "/")) if f.image_path else None,
            "createdAt": f.created_at.isoformat(),
        }
        for f in faces
    ]

    return api_response(
        code=200,
        message="success",
        data=items,
    )


def _notify_ai_cache(path: str, payload: dict):
    try:
        requests.post(
            f"{AI_SERVICE_URL}/cache/{path}",
            json=payload,
            timeout=5,
        )
    except Exception:
        pass
