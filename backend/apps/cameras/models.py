from django.db import models


class Camera(models.Model):
    class Status(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        DISABLED = "disabled", "Disabled"

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=64, unique=True)
    stream_url = models.CharField(max_length=512, blank=True, default="")
    processed_stream_url = models.CharField(max_length=512, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OFFLINE)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "camera"
        ordering = ["id"]

    def __str__(self):
        return f"{self.code} - {self.name}"
