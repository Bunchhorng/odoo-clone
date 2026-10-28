"""Bounded, company-scoped CSV transfers for Contacts and Products."""
import csv
import hashlib
import io
from uuid import uuid4

from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from apps.companies.access import membership_for
from apps.core.api import APIError, api, json_body
from .catalog import catalog_data, definition, filtered_catalog, prepare_catalog, save_catalog
from .models import CatalogImport, Contact, ProductCategory
from .services import positive_id, record_activity, write_access

MAX_CSV_BYTES = 512 * 1024
MAX_IMPORT_ROWS = 200
MAX_EXPORT_ROWS = 10000
PREVIEW_SECONDS = 600
SALT = "kerp.catalog.import.v1"


def transfer_fields(resource):
    if resource not in ("contacts", "products"):
        raise APIError("CSV transfers are available for contacts and products.", 404)
    _, fields = definition(resource)
    return ["category" if field == "category_id" else field for field in fields]


def csv_text(data):
    value = data.get("csv")
    if not isinstance(value, str) or not value.strip():
        raise APIError("Choose a non-empty UTF-8 CSV file.")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError:
        raise APIError("Use valid UTF-8 text in the CSV file.") from None
    if size > MAX_CSV_BYTES:
        raise APIError("CSV files must be at most 512 KiB.")
    return value


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_rows(resource, text):
    allowed = transfer_fields(resource)
    try:
        reader = csv.reader(io.StringIO(text.removeprefix("\ufeff"), newline=""), strict=True)
        headers = next(reader, [])
        if not headers or any(not field or field not in allowed for field in headers) or len(set(headers)) != len(headers):
            raise APIError("Use unique supported column names from the CSV template.")
        required = {"name", "sku"} if resource == "products" else {"name"}
        if not required.issubset(headers):
            raise APIError("The CSV must include " + ", ".join(sorted(required)) + " columns.")
        rows = []
        for values in reader:
            if not values or not any(value.strip() for value in values):
                continue
            if len(values) != len(headers):
                raise APIError(f"Row {len(rows) + 2} has a different number of columns than the header.")
            rows.append(dict(zip(headers, values)))
            if len(rows) > MAX_IMPORT_ROWS:
                raise APIError("Import at most 200 records at a time.")
        if not rows:
            raise APIError("The CSV has no records to import.")
        return headers, rows
    except csv.Error:
        raise APIError("The CSV is malformed. Check quotes and comma separators.") from None


def row_values(resource, company_id, row):
    _, fields = definition(resource)
    values = {}
    for key, value in row.items():
        value = value.strip()
        if key == "category":
            if not value:
                values["category_id"] = None
            else:
                category = ProductCategory.objects.filter(company_id=company_id, name__iexact=value, is_active=True).first()
                if category is None:
                    raise APIError("Create an active product category with this name before importing.")
                values["category_id"] = category.pk
        elif key in ("is_customer", "is_supplier", "is_active"):
            if not value:
                continue  # Use the model's create default for an empty optional cell.
            if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise APIError(f"{key} must be true/false, yes/no, or 1/0.")
            values[key] = value.lower() in ("true", "1", "yes")
        elif key in fields:
            if not value and key in ("sale_price", "cost_price", "reorder_level", "kind", "unit"):
                continue
            values[key] = value
    return values


def validate_rows(resource, company_id, rows):
    preview, prepared = [], []
    seen = {"sku": set(), "barcode": set(), "email": set()}
    for index, row in enumerate(rows, start=2):
        errors, warnings = [], []
        values = None
        try:
            values = row_values(resource, company_id, row)
            item = prepare_catalog(resource, company_id, values)
            if resource == "products":
                for key in ("sku", "barcode"):
                    value = (getattr(item, key) or "").casefold()
                    if value and value in seen[key]:
                        errors.append(f"Duplicate {key} in this CSV.")
                    if value:
                        seen[key].add(value)
            elif item.email:
                email = item.email.casefold()
                if email in seen["email"] or Contact.objects.filter(company_id=company_id, email__iexact=item.email).exists():
                    warnings.append("A contact with this email already exists. This import creates another contact.")
                seen["email"].add(email)
        except APIError as exc:
            # Never expose a foreign-company object through row validation.
            errors.append(exc.message)
        except ValidationError as exc:
            errors.extend(exc.messages)
        preview.append({"row": index, "name": row.get("name", ""), "values": row, "errors": errors, "warnings": warnings})
        prepared.append(values)
    return preview, prepared


def safe_cell(value):
    text = str(value) if value is not None else ""
    # Defense for a first spreadsheet open; do not claim safety after re-saving in
    # every spreadsheet application. Quoting alone does not stop formulas.
    if text.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠")) or text.startswith(("\t", "\r", "\n")):
        text = "'" + text
    return text


@api(["GET"])
def export_csv(request, company_id, resource):
    membership_for(request.user, company_id)
    fields = transfer_fields(resource)
    output = io.StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(fields)
    if request.GET.get("template") != "true":
        queryset = filtered_catalog(resource, company_id, request.GET)
        if queryset.count() > MAX_EXPORT_ROWS:
            raise APIError("Narrow the filters to export at most 10000 records.")
        for item in queryset.iterator(chunk_size=250):
            data = catalog_data(resource, item)
            if resource == "products":
                data["category"] = data["category_name"]
            writer.writerow([safe_cell(data[field]) for field in fields])
    response = HttpResponse("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{resource}.csv"'
    response["X-Content-Type-Options"] = "nosniff"
    return response


@api(["POST"])
def import_preview(request, company_id, resource):
    transfer_fields(resource)
    data = json_body(request, {"csv"})
    text = csv_text(data)
    headers, rows = parse_rows(resource, text)
    with transaction.atomic():
        write_access(request.user, company_id)
        preview, _ = validate_rows(resource, company_id, rows)
    valid = not any(row["errors"] for row in preview)
    token = signing.dumps({"company": company_id, "user": request.user.pk, "resource": resource,
                          "sha256": fingerprint(text), "nonce": uuid4().hex}, salt=SALT) if valid else None
    return JsonResponse({"headers": headers, "rows": preview, "count": len(rows), "can_import": valid,
                         "token": token, "expires_in": PREVIEW_SECONDS})


@api(["POST"])
def import_commit(request, company_id, resource):
    transfer_fields(resource)
    data = json_body(request, {"csv", "token"})
    text = csv_text(data)
    token = data.get("token")
    if not isinstance(token, str) or not 1 <= len(token) <= 4096:
        raise APIError("Preview this file before importing.")
    try:
        signed = signing.loads(token, salt=SALT, max_age=PREVIEW_SECONDS)
    except (signing.BadSignature, TypeError, ValueError):
        raise APIError("Preview this file again; the preview is invalid or expired.") from None
    nonce = signed.get("nonce") if isinstance(signed, dict) else None
    expected = {"company": company_id, "user": request.user.pk, "resource": resource, "sha256": fingerprint(text), "nonce": nonce}
    if signed != expected or not isinstance(nonce, str) or len(nonce) != 32:
        raise APIError("The file, company or account changed. Preview the file again.")
    _, rows = parse_rows(resource, text)
    with transaction.atomic():
        write_access(request.user, company_id)
        digest = fingerprint(token)
        receipt = CatalogImport.objects.filter(company_id=company_id, token_digest=digest).first()
        if receipt:
            return JsonResponse({"created": receipt.record_count, "replayed": True})
        preview, prepared = validate_rows(resource, company_id, rows)
        if any(row["errors"] for row in preview):
            raise APIError("Records changed since preview. Preview the file again to see current errors.", 409)
        for values in prepared:
            item = save_catalog(resource, company_id, values)
            record_activity(request.user, company_id, resource, item, f"Imported {item.name}")
        CatalogImport.objects.create(company_id=company_id, token_digest=digest, resource=resource, record_count=len(rows))
    return JsonResponse({"created": len(rows), "replayed": False}, status=201)


@api(["POST"])
def bulk_action(request, company_id, resource):
    transfer_fields(resource)
    data = json_body(request, {"ids", "action"})
    ids = data.get("ids")
    if not isinstance(ids, list) or not 1 <= len(ids) <= 100:
        raise APIError("Select between 1 and 100 records on the current page.")
    ids = {positive_id(value) for value in ids}
    if data.get("action") not in ("archive", "restore"):
        raise APIError("Choose archive or restore.")
    active = data["action"] == "restore"
    model, _ = definition(resource)
    with transaction.atomic():
        write_access(request.user, company_id)
        items = list(model.objects.filter(company_id=company_id, pk__in=ids))
        if len(items) != len(ids):
            raise APIError("A selected record is no longer available in this company.", 404)
        changed = [item for item in items if item.is_active != active]
        for item in changed:
            item.is_active = active
            item.updated_at = timezone.now()
            item.save(update_fields=["is_active", "updated_at"])
            record_activity(request.user, company_id, resource, item, f"{'Restored' if active else 'Archived'} {item.name}")
    return JsonResponse({"selected": len(ids), "changed": len(changed)})
