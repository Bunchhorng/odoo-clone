from django.db import migrations


def seed_presets(apps, schema_editor):
    from apps.companies.seeding import seed_company_records
    Company = apps.get_model("companies", "Company")
    Group = apps.get_model("companies", "CompanyAccessGroup")
    Right = apps.get_model("companies", "AppAccessRight")
    Rule = apps.get_model("companies", "AppRecordRule")
    for company in Company.objects.iterator():
        seed_company_records(company, Group, Right, Rule)


class Migration(migrations.Migration):
    dependencies = [("companies", "0006_seed_system_access_groups")]
    operations = [migrations.RunPython(seed_presets, migrations.RunPython.noop)]
