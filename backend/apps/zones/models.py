from django.db import models


class Zone(models.Model):
    class ZoneType(models.TextChoices):
        RESTRICTED = "restricted", "Restricted"
        DANGER = "danger", "Danger"
        WORKSTATION = "workstation", "Workstation"
        GENERAL = "general", "General"

    camera = models.ForeignKey(
        "cameras.Camera",
        on_delete=models.CASCADE,
        related_name="zones",
    )
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=32, choices=ZoneType.choices, default=ZoneType.RESTRICTED)
    points = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "zone"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.camera_id})"
