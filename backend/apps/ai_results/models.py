from django.db import models


class AIEvent(models.Model):
    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_events",
    )
    camera_identifier = models.CharField(max_length=64)
    frame_id = models.CharField(max_length=128, blank=True, default="")
    event_type = models.CharField(max_length=64)
    confidence = models.FloatField(null=True, blank=True)
    bbox = models.JSONField(default=dict, blank=True)
    snapshot_path = models.CharField(max_length=512, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ai_event"
        ordering = ["-occurred_at", "-id"]


class Alert(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        CLOSED = "closed", "Closed"

    event = models.OneToOneField(AIEvent, on_delete=models.CASCADE, related_name="alert")
    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    event_type = models.CharField(max_length=64)
    level = models.CharField(max_length=32, default="medium")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    title = models.CharField(max_length=128)
    description = models.TextField(blank=True, default="")
    snapshot_path = models.CharField(max_length=512, blank=True, default="")
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alert"
        ordering = ["-occurred_at", "-id"]
