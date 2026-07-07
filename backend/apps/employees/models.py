from django.db import models


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "在职"
        INACTIVE = "inactive", "停用"

    employee_no = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="工号",
    )
    name = models.CharField(max_length=64, verbose_name="姓名")
    department = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="部门",
    )
    position = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="岗位",
    )
    phone = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="手机号",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="状态",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "employee"
        ordering = ["-created_at"]
