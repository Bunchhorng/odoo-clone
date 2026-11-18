from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("business", "0013_transfers_customer_returns")]

    operations = [
        migrations.AddField(
            model_name="stocktransfer",
            name="payload_digest",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="customerreturn",
            name="payload_digest",
            field=models.CharField(default="", max_length=64),
            preserve_default=False,
        ),
        migrations.RemoveConstraint(
            model_name="customerreturnline",
            name="business_customer_return_line",
        ),
        migrations.AddConstraint(
            model_name="customerreturnline",
            constraint=models.UniqueConstraint(
                fields=("customer_return", "delivery_movement"),
                name="business_customer_return_delivery",
            ),
        ),
    ]
