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
            name="Zone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("restricted", "Restricted"),
                            ("danger", "Danger"),
                            ("workstation", "Workstation"),
                            ("general", "General"),
                        ],
                        default="restricted",
                        max_length=32,
                    ),
                ),
                ("points", models.JSONField(blank=True, default=list)),
                ("enabled", models.BooleanField(default=True)),
                ("description", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "camera",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="zones",
                        to="cameras.camera",
                    ),
                ),
            ],
            options={
                "db_table": "zone",
                "ordering": ["id"],
            },
        ),
    ]
