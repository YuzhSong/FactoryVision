from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("cameras", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="camera",
            name="include_faces",
            field=models.BooleanField(default=False),
        ),
    ]
