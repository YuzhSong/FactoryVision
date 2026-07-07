from rest_framework import serializers

from .models import Employee


class EmployeePlaceholderSerializer(serializers.Serializer):
    """保留原占位序列化器，供占位接口使用。"""

    module = serializers.CharField(default="employees")
    status = serializers.CharField(default="placeholder")


class EmployeeCreateSerializer(serializers.Serializer):
    """创建员工——参数校验。"""

    employeeNo = serializers.CharField(required=True, max_length=64)
    name = serializers.CharField(required=True, max_length=64)
    department = serializers.CharField(required=False, max_length=128, default="")
    position = serializers.CharField(required=False, max_length=128, default="")
    phone = serializers.CharField(required=False, max_length=32, default="")


class EmployeeListSerializer(serializers.ModelSerializer):
    """员工列表输出。"""

    employeeNo = serializers.CharField(source="employee_no")

    class Meta:
        model = Employee
        fields = ("id", "employeeNo", "name", "department", "position", "phone", "status")
        read_only_fields = fields
