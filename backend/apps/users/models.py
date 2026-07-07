from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "管理员"
        OPERATOR = "operator", "安保员"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.OPERATOR,
        verbose_name="角色",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user"
        ordering = ["-date_joined"]
