"""Assign endpoints in place. Never create, renumber or re-quantity a movement."""
from django.db import migrations


def assign_legacy_locations(apps, schema_editor):
    alias = schema_editor.connection.alias
    Company = apps.get_model("companies", "Company")
    Location = apps.get_model("business", "StockLocation")
    Warehouse = apps.get_model("business", "Warehouse")
    Movement = apps.get_model("business", "StockMovement")

    # Fail before changing data if legacy relations already cross company bounds.
    for row in Movement.objects.using(alias).select_related("product", "order", "return_of", "reversal_of").iterator(chunk_size=1000):
        relations = [row.product, row.order, row.return_of, row.reversal_of]
        if any(item is not None and item.company_id != row.company_id for item in relations):
            raise RuntimeError(f"Stock movement {row.pk} has a cross-company legacy reference. Inspect it before retrying INV-01.")
        if bool(row.source_location_id) != bool(row.destination_location_id):
            raise RuntimeError(f"Stock movement {row.pk} has only one location. Inspect it before retrying INV-01.")

    inferred, unexpected_signs, zero_rows = 0, 0, 0
    for company_id in Company.objects.using(alias).order_by("pk").values_list("pk", flat=True).iterator():
        virtuals = {}
        for usage, name, code in (("supplier", "Suppliers", "SUPPLIERS"), ("customer", "Customers", "CUSTOMERS"), ("inventory", "Inventory adjustments", "ADJUSTMENTS")):
            location, _ = Location.objects.using(alias).get_or_create(company_id=company_id, system_key=usage,
                defaults={"name": name, "code": code, "usage": usage})
            virtuals[usage] = location.pk
        stock, _ = Location.objects.using(alias).get_or_create(company_id=company_id, system_key="stock",
            defaults={"name": "Main warehouse stock", "code": "WH/STOCK", "usage": "internal"})
        Warehouse.objects.using(alias).get_or_create(company_id=company_id, system_key="default",
            defaults={"name": "Main Warehouse", "code": "WH", "stock_location_id": stock.pk})
        # Original rows can be classified without assuming a purchase-line order.
        pending = []
        originals = Movement.objects.using(alias).filter(company_id=company_id, source_location__isnull=True,
            return_of__isnull=True, reversal_of__isnull=True).select_related("order").order_by("pk")
        for row in originals.iterator(chunk_size=1000):
            kind = row.order.kind if row.order_id else None
            external = virtuals["supplier" if kind == "purchase" else "customer" if kind == "sale" else "inventory"]
            row.source_location_id, row.destination_location_id = (external, stock.pk) if row.quantity >= 0 else (stock.pk, external)
            row.location_inferred = True
            inferred += 1
            zero_rows += row.quantity == 0
            unexpected_signs += bool((kind == "sale" and row.quantity > 0) or (kind == "purchase" and row.quantity < 0))
            pending.append(row)
            if len(pending) == 1000:
                Movement.objects.using(alias).bulk_update(pending, ["source_location", "destination_location", "location_inferred"])
                pending = []
        if pending:
            Movement.objects.using(alias).bulk_update(pending, ["source_location", "destination_location", "location_inferred"])

        # Reverse the actual original endpoints for returns/reversals. Multiple
        # passes also handle imported references not ordered by primary key.
        remaining = Movement.objects.using(alias).filter(company_id=company_id, source_location__isnull=True)
        while remaining.exists():
            processed = 0
            for row in remaining.select_related("return_of", "reversal_of").iterator(chunk_size=1000):
                original = row.return_of or row.reversal_of
                if original is None or not original.source_location_id or not original.destination_location_id:
                    continue
                if row.return_of_id and (row.quantity >= 0 or original.quantity <= 0 or -row.quantity > original.quantity):
                    raise RuntimeError(f"Legacy supplier return {row.pk} has inconsistent quantities; inspect before retrying INV-01.")
                if row.reversal_of_id and row.quantity != -original.quantity:
                    raise RuntimeError(f"Legacy reversal {row.pk} does not reverse its source quantity; inspect before retrying INV-01.")
                Movement.objects.using(alias).filter(pk=row.pk).update(source_location_id=original.destination_location_id,
                    destination_location_id=original.source_location_id, location_inferred=True)
                inferred += 1
                processed += 1
            if not processed:
                raise RuntimeError("Legacy stock correction references contain a cycle or missing endpoints. Inspect before retrying INV-01.")
    print(f" INV-01: assigned {inferred} existing movements in place; {zero_rows} zero-quantity and {unexpected_signs} unusual-sign originals retained. All historical physical locations are inferred.")


class Migration(migrations.Migration):
    dependencies = [("business", "0007_warehouse_location_schema")]
    operations = [migrations.RunPython(assign_legacy_locations, migrations.RunPython.noop, atomic=True)]
