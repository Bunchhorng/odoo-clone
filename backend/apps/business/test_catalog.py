import csv
import io
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.companies.models import Company, CompanyMembership
from .catalog import save_catalog
from .models import Activity, CatalogImport, Contact, Product, ProductCategory, StockMovement


class CatalogModuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user("catalog-owner@example.com")
        cls.member = get_user_model().objects.create_user("catalog-member@example.com")
        cls.company = Company.objects.create(name="Catalog", slug="catalog")
        cls.other = Company.objects.create(name="Other catalog", slug="other-catalog")
        for company in (cls.company, cls.other):
            CompanyMembership.objects.create(company=company, user=cls.owner, role="owner")
        CompanyMembership.objects.create(company=cls.company, user=cls.member)
        cls.category = ProductCategory.objects.create(company=cls.company, name="Furniture")
        cls.foreign_category = ProductCategory.objects.create(company=cls.other, name="Private category")
        cls.customer = Contact.objects.create(company=cls.company, name="Alice", email="alice@example.com", phone="012345")
        cls.supplier = Contact.objects.create(company=cls.company, name="Bob", is_customer=False, is_supplier=True)
        cls.foreign_contact = Contact.objects.create(company=cls.other, name="Private contact")
        cls.product = Product.objects.create(company=cls.company, name="Desk", sku="DESK", category=cls.category, barcode="0012345", sale_price="25", reorder_level="2")

    def setUp(self):
        self.client.force_login(self.owner)
        self.base = f"/api/v1/companies/{self.company.pk}/erp/"

    def call(self, method, path, data=None, status=200):
        response = getattr(self.client, method)(self.base + path, data=data, content_type="application/json")
        self.assertEqual(response.status_code, status, response.content.decode())
        return response.json()

    def preview(self, resource, text):
        return self.call("post", f"{resource}/import/preview/", {"csv": text})

    def commit(self, resource, text, preview, status=201):
        return self.call("post", f"{resource}/import/", {"csv": text, "token": preview["token"]}, status)

    def test_categories_are_company_scoped_and_archive_keeps_existing_relations(self):
        self.call("post", "product-categories/", {"name": "Furniture"}, 400)
        self.call("patch", f"product-categories/{self.category.pk}/", {"is_active": False})
        kept = self.call("patch", f"products/{self.product.pk}/", {"name": "Renamed desk", "category_id": self.category.pk})
        self.assertEqual(kept["category_name"], "Furniture")
        self.call("post", "products/", {"name": "New", "sku": "NEW", "category_id": self.category.pk}, 400)
        self.call("patch", f"products/{self.product.pk}/", {"category_id": self.foreign_category.pk}, 404)
        self.call("get", f"product-categories/{self.foreign_category.pk}/", status=404)
        self.call("post", "product-categories/", {"name": "Supplies"}, 201)

    def test_barcodes_are_unique_per_company_and_allow_multiple_empty_values(self):
        for sku in ("A", "B"):
            item = self.call("post", "products/", {"name": sku, "sku": sku, "barcode": ""}, 201)
            self.assertEqual(item["barcode"], "")
        self.call("post", "products/", {"name": "Duplicate", "sku": "C", "barcode": "0012345"}, 400)
        Product.objects.create(company=self.other, name="Private", sku="C", barcode="0012345")
        self.assertEqual(self.call("get", f"products/{self.product.pk}/")["barcode"], "0012345")

    def test_contact_filters_and_phone_search(self):
        self.assertEqual(self.call("get", "contacts/?role=customer")["count"], 1)
        self.assertEqual(self.call("get", "contacts/?role=supplier")["results"][0]["name"], "Bob")
        self.assertEqual(self.call("get", "contacts/?role=both")["count"], 0)
        self.assertEqual(self.call("get", "contacts/?q=012345")["count"], 1)
        self.call("get", "contacts/?role=invalid", status=400)

    def test_product_filters_and_zero_stock_annotation(self):
        service = Product.objects.create(company=self.company, name="Service", sku="SERVICE", kind="service")
        self.assertEqual(self.call("get", "products/?stock=out")["results"][0]["id"], self.product.pk)
        StockMovement.objects.create(company=self.company, product=self.product, quantity=3, reason="Opening", actor_email=self.owner.email)
        self.assertEqual(self.call("get", "products/?stock=low")["count"], 0)
        self.assertEqual(self.call("get", f"products/?category_id={self.category.pk}")["count"], 1)
        self.assertEqual(self.call("get", "products/?category_id=none")["results"][0]["id"], service.pk)
        self.assertEqual(self.call("get", "products/?kind=service")["count"], 1)
        for query in ("q=0012345", "q=Furniture"):
            self.assertEqual(self.call("get", "products/?" + query)["results"][0]["id"], self.product.pk)
        for query in ("stock=bad", "kind=bad", "category_id=²", "ordering=company__name"):
            self.call("get", "products/?" + query, status=400)
        self.call("get", f"products/?category_id={self.foreign_category.pk}", status=404)

    def test_sorting_is_stable_and_allowlisted(self):
        Contact.objects.create(company=self.company, name="Alice")
        names = [row["name"] for row in self.call("get", "contacts/?ordering=name")["results"]]
        self.assertEqual(names, ["Alice", "Alice", "Bob"])
        self.assertEqual(self.call("get", "contacts/?ordering=-name")["results"][0]["name"], "Bob")
        for ordering in ("password", "name,-id", "--name", "?"):
            self.call("get", "contacts/?ordering=" + ordering, status=400)

    def test_bulk_archive_restore_is_atomic_and_idempotent(self):
        ids = [self.customer.pk, self.supplier.pk, self.customer.pk]
        first = self.call("post", "contacts/bulk/", {"ids": ids, "action": "archive"})
        self.assertEqual(first, {"selected": 2, "changed": 2})
        self.assertEqual(self.call("post", "contacts/bulk/", {"ids": ids, "action": "archive"})["changed"], 0)
        self.assertEqual(Activity.objects.filter(resource="contacts").count(), 2)
        self.call("post", "contacts/bulk/", {"ids": [self.customer.pk, self.foreign_contact.pk], "action": "restore"}, 404)
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)
        self.assertEqual(self.call("post", "contacts/bulk/", {"ids": ids, "action": "restore"})["changed"], 2)

    def test_bulk_validates_sizes_actions_and_identifiers(self):
        for ids in ([], [self.customer.pk] * 101, [True], ["²"], ["9" * 5000], "1"):
            self.call("post", "contacts/bulk/", {"ids": ids, "action": "archive"}, 400)
        self.call("post", "contacts/bulk/", {"ids": [self.customer.pk], "action": "delete"}, 400)
        self.call("post", "tasks/bulk/", {"ids": [self.customer.pk], "action": "archive"}, 404)

    def test_member_can_read_export_but_cannot_manage_categories_bulk_or_import(self):
        text = "name\nNew person\n"
        preview = self.preview("contacts", text)
        self.client.force_login(self.member)
        self.call("post", "contacts/import/preview/", {"csv": text}, 403)
        self.commit("contacts", text, preview, 400)  # Preview is bound to the requesting account.
        self.call("post", "contacts/bulk/", {"ids": [self.customer.pk], "action": "archive"}, 403)
        self.call("post", "product-categories/", {"name": "Denied"}, 403)
        self.assertEqual(self.client.get(self.base + "contacts/export/").status_code, 200)

    def test_export_obeys_filters_and_escapes_spreadsheet_formulas(self):
        Contact.objects.create(company=self.company, name='=SUM(1,2)', notes='Two lines\nwith "quotes"', is_supplier=True)
        response = self.client.get(self.base + "contacts/export/?role=customer&ordering=name")
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 2)
        escaped = next(row for row in rows if row["name"].startswith("'="))
        self.assertEqual(escaped["notes"], 'Two lines\nwith "quotes"')
        self.assertNotIn("Private contact", response.content.decode())
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_template_and_product_export_use_importable_columns(self):
        template = self.client.get(self.base + "products/export/?template=true")
        self.assertEqual(len(list(csv.reader(io.StringIO(template.content.decode("utf-8-sig"))))), 1)
        response = self.client.get(self.base + "products/export/")
        row = next(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(row["category"], "Furniture")
        self.assertEqual(row["barcode"], "0012345")
        self.assertNotIn("stock_quantity", row)
        self.assertNotIn("company_id", row)

    def test_preview_reports_errors_without_writing_records(self):
        before = (Product.objects.count(), Activity.objects.count(), CatalogImport.objects.count())
        preview = self.preview("products", "name,sku,sale_price\nGood,NEW,10\nBad,OTHER,-1\n")
        self.assertFalse(preview["can_import"])
        self.assertIsNone(preview["token"])
        self.assertTrue(preview["rows"][1]["errors"])
        self.assertEqual((Product.objects.count(), Activity.objects.count(), CatalogImport.objects.count()), before)

    def test_import_creates_products_with_category_and_preserved_barcode(self):
        text = "\ufeffname,sku,category,barcode,sale_price,unit\r\nImported desk,imp,Furniture,000099,12.50,Units\r\n"
        preview = self.preview("products", text)
        self.assertTrue(preview["can_import"], preview)
        result = self.commit("products", text, preview)
        self.assertEqual(result, {"created": 1, "replayed": False})
        product = Product.objects.get(company=self.company, sku="IMP")
        self.assertEqual(product.category_id, self.category.pk)
        self.assertEqual(product.barcode, "000099")
        self.assertEqual(str(product.sale_price), "12.50")
        self.assertEqual(Activity.objects.filter(resource="products", record_id=product.pk).count(), 1)

    def test_contact_import_warns_about_duplicate_email_and_parses_booleans(self):
        text = 'name,email,is_customer,is_supplier,is_active,notes\n"Alice, second",alice@example.com,no,yes,true,"Line 1\nLine 2"\n'
        preview = self.preview("contacts", text)
        self.assertTrue(preview["can_import"])
        self.assertTrue(preview["rows"][0]["warnings"])
        self.commit("contacts", text, preview)
        contact = Contact.objects.get(company=self.company, name="Alice, second")
        self.assertFalse(contact.is_customer)
        self.assertTrue(contact.is_supplier)
        self.assertEqual(contact.notes, "Line 1\nLine 2")

    def test_commit_retry_creates_records_and_activity_only_once(self):
        for resource, text in (("contacts", "name\nRetry contact\n"), ("products", "name,sku\nRetry product,RETRY\n")):
            preview = self.preview(resource, text)
            self.commit(resource, text, preview)
            retried = self.commit(resource, text, preview, 200)
            self.assertEqual(retried, {"created": 1, "replayed": True})
        self.assertEqual(Contact.objects.filter(name="Retry contact").count(), 1)
        self.assertEqual(Activity.objects.filter(summary="Imported Retry contact").count(), 1)
        self.assertEqual(CatalogImport.objects.count(), 2)

    def test_preview_token_is_bound_to_file_company_resource_and_user(self):
        text = "name\nBound contact\n"
        preview = self.preview("contacts", text)
        self.commit("contacts", text + "Different\n", preview, 400)
        self.commit("products", text, preview, 400)
        self.base = f"/api/v1/companies/{self.other.pk}/erp/"
        self.commit("contacts", text, preview, 400)

    def test_expired_or_malformed_preview_tokens_are_rejected(self):
        text = "name\nExpired\n"
        preview = self.preview("contacts", text)
        with patch("django.core.signing.time.time", return_value=time.time() + 601):
            self.commit("contacts", text, preview, 400)
        for token in (None, True, [], {}, "broken", "x" * 4097):
            self.call("post", "contacts/import/", {"csv": text, "token": token}, 400)

    def test_commit_revalidates_after_another_writer_takes_the_sku(self):
        text = "name,sku\nFirst,FIRST\nSecond,SECOND\n"
        preview = self.preview("products", text)
        Product.objects.create(company=self.company, name="Taken", sku="SECOND")
        self.commit("products", text, preview, 409)
        self.assertFalse(Product.objects.filter(sku="FIRST").exists())
        self.assertFalse(CatalogImport.objects.exists())

    def test_transaction_rolls_back_earlier_rows_when_a_later_save_fails(self):
        text = "name\nFirst contact\nSecond contact\n"
        preview = self.preview("contacts", text)
        count = 0

        def failing_save(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise ValidationError("A row changed during import.")
            return save_catalog(*args, **kwargs)

        with patch("apps.business.catalog_transfer.save_catalog", side_effect=failing_save):
            self.commit("contacts", text, preview, 400)
        self.assertFalse(Contact.objects.filter(name="First contact").exists())
        self.assertFalse(Activity.objects.exists())
        self.assertFalse(CatalogImport.objects.exists())

    def test_preview_catches_duplicate_skus_barcodes_and_unknown_categories(self):
        for text in (
            "name,sku\nOne,dup\nTwo,DUP\n",
            "name,sku,barcode\nOne,A,0001\nTwo,B,0001\n",
            "name,sku,barcode\nOne,A,0012345\n",
            "name,sku,category\nOne,A,Private category\n",
        ):
            preview = self.preview("products", text)
            self.assertFalse(preview["can_import"], preview)
        self.category.is_active = False
        self.category.save()
        self.assertFalse(self.preview("products", "name,sku,category\nOne,A,Furniture\n")["can_import"])

    def test_csv_headers_structure_and_row_limit_are_validated(self):
        for text in ("name,name\nA,B", "company_id,name\n1,B", "email\na@example.com", "name\n", 'name\n"unfinished', "name,email\nA,B,C", "name\n" + "Person\n" * 201):
            self.call("post", "contacts/import/preview/", {"csv": text}, 400)
        self.assertTrue(self.preview("contacts", "name\n\nPerson\n\n")["can_import"])

    def test_csv_size_encoding_and_boolean_errors_are_bounded(self):
        for text in (None, [], "name\n" + "x" * 524288, "name\n\ud800"):
            self.call("post", "contacts/import/preview/", {"csv": text}, 400)
        preview = self.preview("contacts", "name,is_customer\nBad,maybe\n")
        self.assertFalse(preview["can_import"])

    def test_separate_confirmed_previews_allow_explicit_new_contact_imports(self):
        text = "name\nIntentional new contact\n"
        previews = [self.preview("contacts", text), self.preview("contacts", text)]
        self.assertNotEqual(previews[0]["token"], previews[1]["token"])
        for preview in previews:
            self.commit("contacts", text, preview)
        self.assertEqual(Contact.objects.filter(name="Intentional new contact").count(), 2)
