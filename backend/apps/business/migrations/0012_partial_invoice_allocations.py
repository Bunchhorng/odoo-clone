from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


def copy_legacy_invoice_lines(apps, schema_editor):
    Invoice, InvoiceLine, OrderLine = (apps.get_model("business", name) for name in ("Invoice", "InvoiceLine", "OrderLine"))
    for invoice in Invoice.objects.all().iterator():
        for line in OrderLine.objects.filter(order_id=invoice.order_id):
            ratio = Decimal("1")
            InvoiceLine.objects.create(invoice_id=invoice.pk, order_line_id=line.pk, quantity=line.quantity,
                description=line.description, unit_price=line.unit_price, tax_rate=line.tax_rate,
                subtotal=line.subtotal * ratio, tax_total=line.tax_total * ratio, total=line.total * ratio)


class Migration(migrations.Migration):
    dependencies = [("business", "0011_delivery_operations")]
    operations = [
        migrations.AlterField(model_name="invoice", name="order", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="invoices", to="business.order")),
        migrations.AddField(model_name="invoice", name="request_id", field=models.UUIDField(blank=True, null=True, unique=True)),
        migrations.AddField(model_name="invoice", name="payload_digest", field=models.CharField(blank=True, max_length=64)),
        migrations.CreateModel(name="InvoiceLine", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("quantity", models.DecimalField(decimal_places=3, max_digits=12)), ("description", models.CharField(max_length=300)),
            ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)), ("tax_rate", models.DecimalField(decimal_places=2, max_digits=5)),
            ("subtotal", models.DecimalField(decimal_places=2, max_digits=16)), ("tax_total", models.DecimalField(decimal_places=2, max_digits=16)), ("total", models.DecimalField(decimal_places=2, max_digits=16)),
            ("invoice", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="lines", to="business.invoice")),
            ("order_line", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="invoice_lines", to="business.orderline")),
        ], options={"ordering": ("id",), "constraints": [models.UniqueConstraint(fields=("invoice", "order_line"), name="business_invoice_order_line")] }),
        migrations.RunPython(copy_legacy_invoice_lines, migrations.RunPython.noop),
    ]
