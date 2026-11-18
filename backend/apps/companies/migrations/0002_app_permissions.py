from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyAccessGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("code", models.SlugField(max_length=64)),
                ("is_system", models.BooleanField(default=False)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="access_groups", to="companies.company")),
            ],
            options={"ordering": ("name", "id")},
        ),
        migrations.CreateModel(
            name="CompanyAccessGroupMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="companies.companyaccessgroup")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="company_access_groups", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AppAccessRight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_key", models.SlugField(max_length=64)),
                ("can_read", models.BooleanField(default=False)),
                ("can_create", models.BooleanField(default=False)),
                ("can_write", models.BooleanField(default=False)),
                ("can_delete", models.BooleanField(default=False)),
                ("can_approve", models.BooleanField(default=False)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="app_access_rights", to="companies.company")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="app_access_rights", to="companies.companyaccessgroup")),
            ],
        ),
        migrations.CreateModel(
            name="UserAppAccessOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_key", models.SlugField(max_length=64)),
                ("can_read", models.BooleanField(blank=True, null=True)),
                ("can_create", models.BooleanField(blank=True, null=True)),
                ("can_write", models.BooleanField(blank=True, null=True)),
                ("can_delete", models.BooleanField(blank=True, null=True)),
                ("can_approve", models.BooleanField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_app_access_overrides", to="companies.company")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="app_access_overrides", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AppRecordRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("app_key", models.SlugField(max_length=64)),
                ("model_key", models.SlugField(max_length=100)),
                ("scope", models.CharField(choices=[("all_company", "All company records"), ("own", "Own records"), ("assigned", "Assigned records")], max_length=20)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="app_record_rules", to="companies.company")),
                ("group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="record_rules", to="companies.companyaccessgroup")),
            ],
        ),
        migrations.AddConstraint(model_name="companyaccessgroup", constraint=models.UniqueConstraint(fields=("company", "code"), name="companies_access_group_code")),
        migrations.AddConstraint(model_name="companyaccessgroupmembership", constraint=models.UniqueConstraint(fields=("group", "user"), name="companies_access_group_member")),
        migrations.AddConstraint(model_name="appaccessright", constraint=models.UniqueConstraint(fields=("company", "group", "app_key"), name="companies_app_access_right")),
        migrations.AddConstraint(model_name="userappaccessoverride", constraint=models.UniqueConstraint(fields=("company", "user", "app_key"), name="companies_user_app_override")),
        migrations.AddConstraint(model_name="apprecordrule", constraint=models.UniqueConstraint(fields=("company", "group", "app_key", "model_key", "scope"), name="companies_app_record_rule")),
    ]
