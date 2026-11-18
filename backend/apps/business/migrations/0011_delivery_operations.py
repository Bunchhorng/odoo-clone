from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("business", "0010_stock_reservations")]
    operations = [
        migrations.CreateModel(
            name="StockOperation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("number", models.CharField(max_length=30)), ("request_id", models.UUIDField(unique=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("done", "Done"), ("cancelled", "Cancelled")], default="draft", max_length=12)),
                ("actor_email", models.EmailField(max_length=254)),
                ("backorder_of", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="backorder", to="business.stockoperation")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="companies.company")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_operations", to="business.order")),
                ("source_location", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="delivery_operations", to="business.stocklocation")),
            ], options={"ordering": ("-id",), "constraints": [models.UniqueConstraint(fields=("company", "number"), name="business_company_operation_number")]},
        ),
        migrations.CreateModel(
            name="StockOperationLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=300)), ("planned_quantity", models.DecimalField(decimal_places=3, max_digits=12)), ("done_quantity", models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ("operation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="business.stockoperation")),
                ("order_line", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operation_lines", to="business.orderline")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operation_lines", to="business.product")),
            ], options={"ordering": ("id",), "constraints": [models.UniqueConstraint(fields=("operation", "order_line"), name="business_operation_order_line")]},
        ),
        migrations.AddField(model_name="stockreservation", name="operation", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reservations", to="business.stockoperation")),
        migrations.AddField(model_name="stockmovement", name="operation", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="movements", to="business.stockoperation")),
    ]
