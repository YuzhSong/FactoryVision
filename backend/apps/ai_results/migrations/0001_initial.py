# Generated manually for P0 backend-ai-service integration.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("cameras", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("camera_identifier", models.CharField(max_length=64)),
                ("frame_id", models.CharField(blank=True, default="", max_length=128)),
                ("event_type", models.CharField(max_length=64)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("bbox", models.JSONField(blank=True, default=dict)),
                ("snapshot_path", models.CharField(blank=True, default="", max_length=512)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "camera",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_events",
                        to="cameras.camera",
                    ),
                ),
            ],
            options={
                "db_table": "ai_event",
                "ordering": ["-occurred_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Alert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=64)),
                ("level", models.CharField(default="medium", max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("processing", "Processing"), ("closed", "Closed")],
                        default="pending",
                        max_length=32,
                    ),
                ),
                ("title", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, default="")),
                ("snapshot_path", models.CharField(blank=True, default="", max_length=512)),
                ("occurred_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "camera",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="alerts",
                        to="cameras.camera",
                    ),
                ),
                (
                    "event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="alert",
                        to="ai_results.aievent",
                    ),
                ),
            ],
            options={
                "db_table": "alert",
                "ordering": ["-occurred_at", "-id"],
            },
        ),
    ]
