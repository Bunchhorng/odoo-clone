from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("business", "0002_product_barcode_catalogimport_productcategory_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="opportunity",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name="quotations", to="business.opportunity"),
        ),
        migrations.AddField(model_name="order", name="version", field=models.PositiveIntegerField(default=1)),
        migrations.AddField(model_name="invoice", name="version", field=models.PositiveIntegerField(default=1)),
    ]
