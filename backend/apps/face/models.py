from django.db import models


class FaceFeature(models.Model):
    class FaceType(models.TextChoices):
        FRONT = "front", "正面"
        LEFT = "left", "左侧"
        RIGHT = "right", "右侧"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="face_features",
        verbose_name="关联员工",
    )
    feature_vector = models.JSONField(verbose_name="人脸特征向量")
    image_path = models.CharField(
        max_length=255, blank=True, default="", verbose_name="原始图片路径"
    )
    face_type = models.CharField(
        max_length=32,
        choices=FaceType.choices,
        verbose_name="人脸角度",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "face_feature"
        ordering = ["employee", "face_type"]
