"""Create an isolated, repeatable demo workspace for an existing account."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company, CompanyMembership
from apps.business.models import Activity, Contact, Opportunity, Product, Project, StockMovement, Task, WorkspaceSettings
from apps.business.services import fulfill_order, invoice_order, register_payment, save_order
from apps.business.accounting import post_invoice


class Command(BaseCommand):
    help = "Create a separate demo company for an existing active user. Existing demo companies are left unchanged."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Existing user's email; no account password is created or changed.")

    @transaction.atomic
    def handle(self, *args, **options):
        user = get_user_model().objects.filter(email__iexact=options["email"], is_active=True).first()
        if user is None:
            raise CommandError("Create an active user account first, then supply its email.")
        slug = f"kerp-demo-{user.pk}"
        company, created = Company.objects.get_or_create(slug=slug, defaults={"name": "KERP Demo"})
        if not created:
            self.stdout.write("Demo company already exists; no records were changed.")
            return
        CompanyMembership.objects.create(company=company, user=user, role="owner")
        WorkspaceSettings.objects.create(company=company, currency="USD")
        contacts = []
        for index, (name, organization) in enumerate([
            ("Olivia Martin", "Azure Interiors"), ("James Wilson", "Cedar & Co."),
            ("Sophia Chen", "Harbor Ventures"), ("Daniel Brooks", "Northstar Supply"),
            ("Emma Thompson", "Atelier Goods"), ("Liam Davis", "Evergreen Studio"),
        ]):
            contacts.append(Contact.objects.create(company=company, name=name, organization=organization,
                email=f"contact{index + 1}@example.test", phone=f"+1 555 010 {index + 1:04d}",
                country="United States", address=f"{100 + index} Example Avenue\nSample City",
                is_customer=True, is_supplier=index in (3, 4), notes="Sample record created by seed_demo."))
        products = []
        for sku, name, kind, price, cost in [
            ("DESK-01", "Oak writing desk", "goods", "390", "210"),
            ("CHAIR-01", "Ergonomic office chair", "goods", "180", "95"),
            ("MON-27", "27-inch monitor", "goods", "310", "220"),
            ("LAMP-01", "Adjustable desk lamp", "goods", "48", "24"),
            ("SHELF-01", "Modular bookcase", "goods", "260", "140"),
            ("STAND-01", "Laptop stand", "goods", "45", "18"),
            ("SETUP-01", "Workspace installation", "service", "250", "100"),
            ("CONSULT", "Design consultation", "service", "120", "60"),
        ]:
            product = Product.objects.create(company=company, sku=sku, name=name, kind=kind,
                sale_price=price, cost_price=cost, reorder_level=10, unit="Hours" if kind == "service" else "Units")
            products.append(product)
            if kind == "goods":
                StockMovement.objects.create(company=company, product=product, quantity=5 if sku == "LAMP-01" else 40,
                    reason="Demo opening stock", actor_email=user.email)
        for title, contact_index, stage, value, probability in [
            ("New studio workspace", 0, "new", "4200", 15),
            ("Office refresh — 20 desks", 1, "qualified", "12000", 40),
            ("Harbor meeting rooms", 2, "proposition", "8500", 70),
            ("Atelier retail fit-out", 4, "qualified", "6400", 45),
            ("Evergreen design package", 5, "won", "2400", 100),
        ]:
            Opportunity.objects.create(company=company, title=title, contact=contacts[contact_index], stage=stage,
                expected_revenue=value, probability=probability, expected_date=timezone.localdate() + timedelta(days=14),
                notes="Sample opportunity. Open this record to edit its details.")

        def order(kind, contact, product, quantity, confirmed=False):
            result = save_order(company.pk, {"kind": kind, "contact_id": contact.pk,
                "notes": "Sample document for exploring the workflow.",
                "lines": [{"product_id": product.pk, "quantity": str(quantity), "tax_rate": "7"}]})
            if confirmed:
                result.status = "confirmed"
                result.save(update_fields=["status"])
            return result

        purchase = order("purchase", contacts[3], products[0], 20, True)
        fulfill_order(purchase, user)
        bill = invoice_order(purchase)
        bill.status = "issued"
        bill.save(update_fields=["status"])
        post_invoice(bill, user.email)
        sale = order("sale", contacts[0], products[0], 4, True)
        fulfill_order(sale, user)
        invoice = invoice_order(sale)
        invoice.status = "issued"
        invoice.save(update_fields=["status"])
        post_invoice(invoice, user.email)
        register_payment(invoice, {"amount": "500", "request_id": str(uuid4()), "reference": "Demo deposit"}, actor_email=user.email)
        paid_sale = order("sale", contacts[5], products[6], 2, True)
        paid_invoice = invoice_order(paid_sale)
        paid_invoice.status = "issued"
        paid_invoice.save(update_fields=["status"])
        post_invoice(paid_invoice, user.email)
        register_payment(paid_invoice, {"amount": str(paid_invoice.total), "request_id": str(uuid4()), "reference": "Demo payment"}, actor_email=user.email)
        order("sale", contacts[1], products[1], 12)
        order("sale", contacts[2], products[2], 6)
        order("purchase", contacts[4], products[3], 30)
        for index, name in enumerate(("Azure office installation", "Harbor meeting rooms", "Internal operations")):
            project = Project.objects.create(company=company, name=name, contact=contacts[index] if index < 2 else None,
                notes="Sample project. Use Open tasks to manage its work.")
            for task_index, (title, stage) in enumerate((("Plan requirements", "done"), ("Prepare workspace", "in_progress"), ("Review and hand over", "todo"))):
                Task.objects.create(company=company, project=project, title=title, stage=stage,
                    priority="high" if task_index == 1 else "normal", assignee=user,
                    due_date=timezone.localdate() + timedelta(days=task_index * 3 - 1))
        Activity.objects.create(company=company, actor_email=user.email, resource="orders", record_id=sale.pk,
            summary="Demo workspace ready: contacts, pipeline, orders, stock, invoices, and projects")
        self.stdout.write(self.style.SUCCESS("Created KERP Demo. Reload KERP and select it in Working in. Existing companies and passwords were preserved."))
