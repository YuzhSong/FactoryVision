from django.db import models


class Event(models.Model):
    class Source(models.TextChoices):
        AI_SERVICE = "ai_service", "AI Service"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Status(models.TextChoices):
        NEW = "new", "New"
        PROCESSING = "processing", "Processing"
        CLOSED = "closed", "Closed"

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    camera_identifier = models.CharField(max_length=64, blank=True, default="")
    event_type = models.CharField(max_length=64)
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.AI_SERVICE)
    severity = models.CharField(max_length=32, choices=Severity.choices, default=Severity.INFO)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NEW)
    occurred_at = models.DateTimeField()
    frame_id = models.CharField(max_length=128, blank=True, default="")
    track_id = models.CharField(max_length=128, blank=True, default="")
    bbox = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    snapshot_path = models.CharField(max_length=512, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "event"
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"{self.event_type} @ {self.camera_identifier or 'unknown'}"
