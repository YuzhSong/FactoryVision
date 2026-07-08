import base64
import os
import re
import uuid
from pathlib import Path

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.employees.models import Employee
from common.response import api_response

from .models import FaceFeature
from .serializers import FaceEnrollResultSerializer, FaceEnrollSerializer

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:9000")
FACE_MEDIA_ROOT = Path(settings.BASE_DIR) / "media" / "faces"


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


def _call_ai_extract(image_base64: str) -> list:
    """
    调用 AI Service 提取人脸编码。

    当前占位，等成员 2 部署 /faces/extract 接口后替换。
    """
    try:
        resp = requests.post(
            f"{AI_SERVICE_URL}/faces/extract",
            json={"imageBase64": image_base64},
            timeout=10,
        )
    except requests.RequestException:
        raise RuntimeError("AI 服务不可用")

    if resp.status_code == 200:
        return resp.json()["data"]["featureVector"]

    msg = resp.json().get("message", "未知错误")
    raise ValueError(msg)


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

                # ① 存盘
                image_path = _save_image(employee_id, face_type, image_b64)
                saved_images.append(image_path)

                # ② 调 AI Service 提取编码
                try:
                    feature_vector = _call_ai_extract(image_b64)
                except RuntimeError:
                    raise  # AI 服务挂了，抛到外层
                except ValueError as e:
                    raise ValueError(f"{face_type}: {e}")

                # ③ 写入 face_feature
                feature = FaceFeature.objects.create(
                    employee_id=employee_id,
                    feature_vector=feature_vector,
                    image_path=image_path,
                    face_type=face_type,
                )
                feature_ids.append(feature.id)
                results.append({"faceType": face_type, "faceFeatureId": feature.id})

    except ValueError as e:
        return api_response(
            code=422,
            message=str(e),
            data=None,
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    except RuntimeError:
        return api_response(
            code=500,
            message="AI 服务暂不可用，请稍后重试",
            data=None,
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return api_response(
        code=200,
        message="success",
        data={"results": results},
    )
