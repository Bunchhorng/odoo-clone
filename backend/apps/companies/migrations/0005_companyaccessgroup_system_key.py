from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("companies", "0004_alter_apprecordrule_model_key")]

    operations = [
        migrations.AddField(
            model_name="companyaccessgroup",
            name="system_key",
            field=models.SlugField(blank=True, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name="companyaccessgroup",
            constraint=models.UniqueConstraint(
                fields=("company", "system_key"),
                name="companies_access_group_system_key",
            ),
        ),
    ]
