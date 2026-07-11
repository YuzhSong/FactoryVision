from django.contrib import admin

from .models import FaceFeature


@admin.register(FaceFeature)
class FaceFeatureAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "face_type", "created_at")
    list_filter = ("face_type", "created_at")
    search_fields = ("employee__name", "employee__employee_no")
