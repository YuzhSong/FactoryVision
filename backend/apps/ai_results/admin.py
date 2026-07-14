from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "event", "event_type", "level", "status", "occurred_at")
    list_filter = ("status", "level", "event_type")
    search_fields = ("event__event_type", "event__camera_identifier", "title")
    list_select_related = ("event", "camera")
