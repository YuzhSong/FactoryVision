from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "camera", "source", "severity", "status", "occurred_at")
    list_filter = ("event_type", "source", "severity", "status")
    search_fields = ("camera_identifier", "frame_id", "track_id")
