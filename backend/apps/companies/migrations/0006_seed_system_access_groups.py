from django.db import migrations


def seed_existing_companies(apps, schema_editor):
    from apps.companies.seeding import seed_company_records, sync_membership_records

    Company = apps.get_model("companies", "Company")
    CompanyMembership = apps.get_model("companies", "CompanyMembership")
    CompanyAccessGroup = apps.get_model("companies", "CompanyAccessGroup")
    CompanyAccessGroupMembership = apps.get_model("companies", "CompanyAccessGroupMembership")
    AppAccessRight = apps.get_model("companies", "AppAccessRight")
    AppRecordRule = apps.get_model("companies", "AppRecordRule")

    for company in Company.objects.all().iterator():
        groups = seed_company_records(company, CompanyAccessGroup, AppAccessRight, AppRecordRule)
        for membership in CompanyMembership.objects.filter(company=company).iterator():
            sync_membership_records(membership, groups, CompanyAccessGroupMembership)


class Migration(migrations.Migration):
    dependencies = [("companies", "0005_companyaccessgroup_system_key")]

    operations = [migrations.RunPython(seed_existing_companies, migrations.RunPython.noop)]
