# Generated manually for P0 backend-ai-service integration.

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Camera",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("code", models.CharField(max_length=64, unique=True)),
                ("stream_url", models.CharField(blank=True, default="", max_length=512)),
                ("processed_stream_url", models.CharField(blank=True, default="", max_length=512)),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("online", "Online"), ("offline", "Offline"), ("disabled", "Disabled")],
                        default="offline",
                        max_length=32,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "camera",
                "ordering": ["id"],
            },
        ),
    ]
