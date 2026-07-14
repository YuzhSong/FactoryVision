from rest_framework import serializers

from .models import FaceFeature

VALID_FACE_TYPES = {"front", "left", "right"}


class FaceImageItemSerializer(serializers.Serializer):
    """单张人脸图片校验。"""

    imageBase64 = serializers.CharField(required=True)
    faceType = serializers.CharField(required=True)
    featureVector = serializers.ListField(
        child=serializers.FloatField(),
        required=False,
        allow_empty=False,
    )
    dimension = serializers.IntegerField(required=False)


class FaceEnrollSerializer(serializers.Serializer):
    """人脸录入请求——校验 3 张图片。"""

    employeeId = serializers.IntegerField(required=True, min_value=1)
    faces = FaceImageItemSerializer(many=True, required=True)

    def validate_faces(self, value):
        if len(value) < 1:
            raise serializers.ValidationError("至少需要 1 张人脸图片")
        if len(value) > 3:
            raise serializers.ValidationError("最多允许 3 张人脸图片")
        seen = set()
        for item in value:
            ft = item["faceType"]
            if ft not in VALID_FACE_TYPES:
                raise serializers.ValidationError(f"无效的人脸角度: {ft}，应为 front/left/right")
            if ft in seen:
                raise serializers.ValidationError(f"人脸角度重复: {ft}")
            seen.add(ft)
        return value


class FaceEnrollResultSerializer(serializers.Serializer):
    """单张人脸录入结果。"""

    faceType = serializers.CharField()
    faceFeatureId = serializers.IntegerField()
