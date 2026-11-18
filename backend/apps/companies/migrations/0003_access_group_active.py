from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0002_app_permissions")]

    operations = [
        migrations.AddField(
            model_name="companyaccessgroup",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
