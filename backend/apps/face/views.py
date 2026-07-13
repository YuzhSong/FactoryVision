import base64
import os
import re
import uuid
import math
from pathlib import Path

import requests
from django.conf import settings
from django.db import transaction
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import OpenApiExample, extend_schema

from apps.employees.models import Employee
from apps.employees.serializers import EmployeeListSerializer
from common.response import api_response

from .models import FaceFeature
from .serializers import FaceEnrollResultSerializer, FaceEnrollSerializer

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:9000")
FACE_MEDIA_ROOT = Path(settings.BASE_DIR) / "media" / "faces"
FACE_FEATURE_DIMENSION = 512
LIVENESS_REQUIRED = os.getenv("LIVENESS_REQUIRED", "False").lower() == "true"


def _ai_service_authorized(request) -> bool:
    expected = str(getattr(settings, "AI_SERVICE_API_TOKEN", "") or "")
    provided = request.headers.get("X-AI-Service-Token", "")
    return bool(expected) and constant_time_compare(expected, provided)


def _serialize_face_library_employee(employee):
    item = EmployeeListSerializer(employee).data
    item["faceFeatures"] = [
        {
            "id": feature.id,
            "featureVector": feature.feature_vector,
            "imagePath": feature.image_path,
            "faceType": feature.face_type,
        }
        for feature in employee.face_features.all()
    ]
    return item


def _save_image(employee_id: int, face_type: str, image_base64: str) -> str:
    """解码 base64 图片并存入本地磁盘，返回相对路径。"""
    clean = re.sub(r"^data:image/\w+;base64,", "", image_base64)
    image_bytes = base64.b64decode(clean)
    timestamp = uuid.uuid4().hex[:8]
    rel_dir = f"{employee_id}"
    abs_dir = FACE_MEDIA_ROOT / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{employee_id}_{face_type}_{timestamp}.jpg"
    filepath = abs_dir / filename
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return str(Path("faces") / rel_dir / filename)


def _call_ai_extract(image_base64: str) -> list[float]:
    """
    调用 AI Service 提取人脸编码。

    Call AI Service and validate one complete face embedding response.
    """
    try:
        resp = requests.post(
            f"{AI_SERVICE_URL}/faces/extract",
            json={"imageBase64": image_base64},
            timeout=60,
        )
    except requests.RequestException:
        raise RuntimeError("AI 服务不可用")

    if resp.status_code == 200:
        try:
            return _validate_feature_payload(resp.json().get("data"), liveness_required=LIVENESS_REQUIRED)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"AI 服务返回了无效的人脸特征: {exc}") from exc

    msg = resp.json().get("message", "未知错误")
    raise ValueError(msg)


def _validate_feature_payload(data: dict, liveness_required: bool = False) -> list[float]:
    """Reject incomplete, non-finite, or unexpected-size embeddings before storage."""
    if not isinstance(data, dict):
        raise ValueError("missing response data")
    if data.get("faceCount") != 1:
        raise ValueError("expected exactly one detected face")
    if data.get("enrollmentAccepted") is False:
        raise ValueError("AI service did not accept the face for enrollment")
    if liveness_required and not (
        data.get("livenessAvailable") is True
        and data.get("livenessPassed") is True
        and data.get("livenessProvider") == "onnx"
    ):
        raise ValueError("a verified liveness provider did not explicitly pass")

    vector = data.get("featureVector")
    dimension = data.get("dimension")
    if not isinstance(vector, list) or dimension != FACE_FEATURE_DIMENSION:
        raise ValueError(f"expected a {FACE_FEATURE_DIMENSION}-dimension feature vector")
    if len(vector) != dimension:
        raise ValueError("feature vector length does not match dimension")

    normalized = []
    for value in vector:
        if isinstance(value, bool):
            raise ValueError("feature vector contains a non-numeric value")
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("feature vector contains a non-numeric value") from exc
        if not math.isfinite(number):
            raise ValueError("feature vector contains a non-finite value")
        normalized.append(number)
    return normalized


def _remove_saved_images(image_paths: list[str]):
    """Remove files written before a later enrollment image invalidates the transaction."""
    for image_path in image_paths:
        try:
            (FACE_MEDIA_ROOT / image_path.removeprefix("faces/")).unlink(missing_ok=True)
        except OSError:
            continue


@api_view(["GET"])
def face_library_view(request):
    """Return active employee embeddings to the configured AI service only."""
    if not _ai_service_authorized(request):
        return api_response(
            code=403,
            message="AI service token required",
            data=None,
            status=status.HTTP_403_FORBIDDEN,
        )

    employees = Employee.objects.filter(status=Employee.Status.ACTIVE).prefetch_related("face_features")
    return api_response(
        data={"items": [_serialize_face_library_employee(employee) for employee in employees]},
        message="success",
    )


@extend_schema(
    summary="人脸录入",
    description="批量录入 3 张人脸图片（正脸/左脸/右脸），全部通过才写入数据库。该接口需要 Bearer JWT 认证。",
    request=FaceEnrollSerializer,
    responses={
        200: None,
        400: None,
        404: None,
        422: None,
        500: None,
    },
    examples=[
        OpenApiExample(
            "Enroll request",
            value={
                "employeeId": 1,
                "faces": [
                    {"imageBase64": "data:image/jpeg;base64,...", "faceType": "front"},
                    {"imageBase64": "data:image/jpeg;base64,...", "faceType": "left"},
                    {"imageBase64": "data:image/jpeg;base64,...", "faceType": "right"},
                ],
            },
            request_only=True,
        ),
        OpenApiExample(
            "Enroll success",
            value={
                "code": 200,
                "message": "success",
                "data": {
                    "results": [
                        {"faceType": "front", "faceFeatureId": 1},
                        {"faceType": "left", "faceFeatureId": 2},
                        {"faceType": "right", "faceFeatureId": 3},
                    ]
                },
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "Employee not found",
            value={
                "code": 404,
                "message": "员工不存在",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["404"],
        ),
        OpenApiExample(
            "No face detected",
            value={
                "code": 422,
                "message": "未检测到人脸",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["422"],
        ),
        OpenApiExample(
            "AI unavailable",
            value={
                "code": 500,
                "message": "AI 服务暂不可用，请稍后重试",
                "data": None,
                "requestId": "uuid",
            },
            response_only=True,
            status_codes=["500"],
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def face_enroll_view(request):
    """
    人脸录入——批量上传 3 张图片（正脸/左脸/右脸）。

    POST /api/face/enroll/
    参数: employeeId, faces[{imageBase64, faceType}]
    返回: results[{faceType, faceFeatureId}]
    """
    serializer = FaceEnrollSerializer(data=request.data)
    if not serializer.is_valid():
        return api_response(
            code=400,
            message="请求参数错误",
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    employee_id = serializer.validated_data["employeeId"]

    if not Employee.objects.filter(id=employee_id).exists():
        return api_response(
            code=404,
            message="员工不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    faces_data = serializer.validated_data["faces"]
    results = []
    saved_images = []
    feature_ids = []

    try:
        with transaction.atomic():
            for item in faces_data:
                face_type = item["faceType"]
                image_b64 = item["imageBase64"]

                # Extract and validate before writing either the image or database record.
                try:
                    if item.get("featureVector"):
                        feature_vector = _validate_feature_payload(
                            {
                                "faceCount": 1,
                                "featureVector": item.get("featureVector"),
                                "dimension": item.get("dimension", FACE_FEATURE_DIMENSION),
                                "enrollmentAccepted": True,
                            },
                            liveness_required=False,
                        )
                    else:
                        feature_vector = _call_ai_extract(image_b64)
                except RuntimeError:
                    raise  # AI 服务挂了，抛到外层
                except ValueError as e:
                    raise ValueError(f"{face_type}: {e}")

                image_path = _save_image(employee_id, face_type, image_b64)
                saved_images.append(image_path)

                feature = FaceFeature.objects.create(
                    employee_id=employee_id,
                    feature_vector=feature_vector,
                    image_path=image_path,
                    face_type=face_type,
                )
                feature_ids.append(feature.id)
                results.append({"faceType": face_type, "faceFeatureId": feature.id})

    except ValueError as e:
        _remove_saved_images(saved_images)
        return api_response(
            code=422,
            message=str(e),
            data=None,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    except RuntimeError:
        _remove_saved_images(saved_images)
        return api_response(
            code=500,
            message="AI 服务暂不可用，请稍后重试",
            data=None,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # 通知 AI Service 刷新人脸库
    _notify_ai_cache("employees/upsert", {"employees": [{"id": employee_id}]})

    return api_response(
        code=200,
        message="success",
        data={"results": results},
    )


@extend_schema(
    summary="删除单张人脸",
    description="删除指定的人脸特征记录和本地图片，并通知 AI Service。该接口需要 Bearer JWT 认证。",
    responses={200: None, 404: None},
    examples=[
        OpenApiExample(
            "删除成功",
            value={"code": 200, "message": "success", "data": {"id": 1}, "requestId": "uuid"},
            response_only=True,
            status_codes=["200"],
        ),
        OpenApiExample(
            "人脸不存在",
            value={"code": 404, "message": "人脸记录不存在", "data": None, "requestId": "uuid"},
            response_only=True,
            status_codes=["404"],
        ),
    ],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def face_delete_view(request, face_id):
    try:
        face = FaceFeature.objects.select_related("employee").get(id=face_id)
    except FaceFeature.DoesNotExist:
        return api_response(
            code=404,
            message="人脸记录不存在",
            data=None,
            status=status.HTTP_404_NOT_FOUND,
        )

    employee_id = face.employee_id
    image_path = face.image_path

    face.delete()

    if image_path:
        abs_path = FACE_MEDIA_ROOT / image_path
        if abs_path.exists():
            abs_path.unlink(missing_ok=True)

    _notify_ai_cache("employees/upsert", {"employees": [{"id": employee_id}]})

    return api_response(
        code=200,
        message="success",
        data={"id": face_id},
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
