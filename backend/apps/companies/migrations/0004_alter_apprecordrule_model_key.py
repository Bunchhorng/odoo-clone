from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0003_access_group_active")]

    operations = [
        migrations.AlterField(
            model_name="apprecordrule",
            name="model_key",
            field=models.CharField(max_length=100),
        ),
    ]
