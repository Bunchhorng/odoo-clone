from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class CompanyRecord(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-id",)


class WorkspaceSettings(models.Model):
    company = models.OneToOneField("companies.Company", on_delete=models.CASCADE)
    currency = models.CharField(max_length=3, default="USD", choices=[
        (code, code) for code in ("USD", "THB", "EUR", "GBP", "SGD", "AUD", "CAD")
    ])


class Contact(CompanyRecord):
    name = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True, max_length=2000)
    country = models.CharField(max_length=100, blank=True)
    is_customer = models.BooleanField(default=True)
    is_supplier = models.BooleanField(default=False)
    notes = models.TextField(blank=True, max_length=10000)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProductCategory(CompanyRecord):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta(CompanyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=("company", "name"), name="business_company_category")]

    def __str__(self):
        return self.name


class CatalogImport(CompanyRecord):
    """Receipt for safe retries; source files and cell contents are not retained."""
    token_digest = models.CharField(max_length=64, unique=True)
    resource = models.CharField(max_length=20)
    record_count = models.PositiveSmallIntegerField()


class Product(CompanyRecord):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    category = models.ForeignKey(ProductCategory, null=True, blank=True, on_delete=models.PROTECT)
    barcode = models.CharField(max_length=64, null=True, blank=True, default=None)
    kind = models.CharField(max_length=12, choices=[("goods", "Goods"), ("service", "Service")], default="goods")
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=30, default="Units")
    reorder_level = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True, max_length=10000)
    is_active = models.BooleanField(default=True)

    class Meta(CompanyRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=("company", "sku"), name="business_company_sku"),
            models.UniqueConstraint(fields=("company", "barcode"), name="business_company_barcode"),
        ]

    def __str__(self):
        return f"{self.sku} — {self.name}"


class Opportunity(CompanyRecord):
    title = models.CharField(max_length=200)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.PROTECT)
    stage = models.CharField(max_length=20, default="new", choices=[
        ("new", "New"), ("qualified", "Qualified"), ("proposition", "Proposition"),
        ("won", "Won"), ("lost", "Lost"),
    ])
    expected_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    probability = models.PositiveSmallIntegerField(default=10, validators=[MaxValueValidator(100)])
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, max_length=10000)
    is_active = models.BooleanField(default=True)


class DocumentSequence(models.Model):
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE)
    prefix = models.CharField(max_length=8)
    value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("company", "prefix"), name="business_company_sequence")]


class Order(CompanyRecord):
    kind = models.CharField(max_length=10, choices=[("sale", "Sale"), ("purchase", "Purchase")])
    opportunity = models.ForeignKey(Opportunity, null=True, blank=True, on_delete=models.PROTECT, related_name="quotations")
    version = models.PositiveIntegerField(default=1)
    number = models.CharField(max_length=30)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField(blank=True)
    contact_address = models.TextField(blank=True)
    currency = models.CharField(max_length=3)
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=12, default="draft", choices=[
        ("draft", "Quotation / RFQ"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled"),
    ])
    notes = models.TextField(blank=True, max_length=10000)
    subtotal = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta(CompanyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=("company", "number"), name="business_company_order_number")]


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    description = models.CharField(max_length=300)
    product_kind = models.CharField(max_length=12)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    subtotal = models.DecimalField(max_digits=16, decimal_places=2)
    tax_total = models.DecimalField(max_digits=16, decimal_places=2)
    total = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        ordering = ("id",)


class PurchaseReceipt(CompanyRecord):
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="receipts")
    number = models.CharField(max_length=30)
    request_id = models.UUIDField(default=uuid4, unique=True)
    payload_digest = models.CharField(max_length=64)
    notes = models.CharField(max_length=300, blank=True)
    actor_email = models.EmailField()

    class Meta(CompanyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=("company", "number"), name="business_company_receipt_number")]


class StockMovement(CompanyRecord):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    order_line = models.ForeignKey(OrderLine, null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    receipt = models.ForeignKey(PurchaseReceipt, null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    request_id = models.UUIDField(null=True, blank=True, unique=True)
    return_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="returns")
    reversal_of = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=300)
    actor_email = models.EmailField()


class Invoice(CompanyRecord):
    kind = models.CharField(max_length=10, choices=[("customer", "Customer Invoice"), ("vendor", "Vendor Bill")])
    version = models.PositiveIntegerField(default=1)
    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="invoice")
    number = models.CharField(max_length=30)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField(blank=True)
    contact_address = models.TextField(blank=True)
    currency = models.CharField(max_length=3)
    date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, default="draft", choices=[
        ("draft", "Draft"), ("issued", "Issued"), ("paid", "Paid"), ("cancelled", "Cancelled"),
    ])
    subtotal = models.DecimalField(max_digits=16, decimal_places=2)
    tax_total = models.DecimalField(max_digits=16, decimal_places=2)
    total = models.DecimalField(max_digits=16, decimal_places=2)
    notes = models.TextField(blank=True, max_length=10000)

    class Meta(CompanyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=("company", "number"), name="business_company_invoice_number")]


class Payment(CompanyRecord):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    request_id = models.UUIDField(unique=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=10, default="bank", choices=[("bank", "Bank"), ("cash", "Cash")])
    reference = models.CharField(max_length=200, blank=True)


class LedgerAccount(CompanyRecord):
    code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=12, choices=[
        ("asset", "Asset"), ("liability", "Liability"), ("income", "Income"), ("expense", "Expense"),
    ])

    class Meta(CompanyRecord.Meta):
        ordering = ("code",)
        constraints = [models.UniqueConstraint(fields=("company", "code"), name="business_company_ledger_account")]


class AccountingSettings(models.Model):
    company = models.OneToOneField("companies.Company", on_delete=models.CASCADE)
    locked_through = models.DateField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)


class JournalEntry(CompanyRecord):
    number = models.CharField(max_length=30)
    source_key = models.CharField(max_length=100)
    kind = models.CharField(max_length=12, choices=[("invoice", "Invoice"), ("payment", "Payment"), ("reversal", "Reversal")])
    journal = models.CharField(max_length=12, choices=[("sales", "Sales"), ("purchases", "Purchases"), ("bank", "Bank"), ("cash", "Cash")])
    date = models.DateField()
    currency = models.CharField(max_length=3)
    description = models.CharField(max_length=300)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="journal_entries")
    payment = models.OneToOneField(Payment, null=True, blank=True, on_delete=models.PROTECT, related_name="journal_entry")
    reversal_of = models.OneToOneField("self", null=True, blank=True, on_delete=models.PROTECT, related_name="reversal")
    actor_email = models.EmailField(blank=True)

    class Meta(CompanyRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=("company", "number"), name="business_company_journal_number"),
            models.UniqueConstraint(fields=("company", "source_key"), name="business_company_journal_source"),
        ]
        indexes = [models.Index(fields=("company", "date"), name="business_journal_date")]


class JournalLine(models.Model):
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(LedgerAccount, on_delete=models.PROTECT, related_name="lines")
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        ordering = ("id",)
        constraints = [models.CheckConstraint(
            condition=(models.Q(debit__gt=0, credit=0) | models.Q(credit__gt=0, debit=0)),
            name="business_journal_line_one_side",
        )]


class Project(CompanyRecord):
    name = models.CharField(max_length=200)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.PROTECT)
    notes = models.TextField(blank=True, max_length=10000)
    is_active = models.BooleanField(default=True)


class Task(CompanyRecord):
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField(max_length=200)
    stage = models.CharField(max_length=20, default="todo", choices=[
        ("todo", "To do"), ("in_progress", "In progress"), ("done", "Done"),
    ])
    priority = models.CharField(max_length=10, default="normal", choices=[("low", "Low"), ("normal", "Normal"), ("high", "High")])
    due_date = models.DateField(null=True, blank=True)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True, max_length=10000)
    is_active = models.BooleanField(default=True)


class Activity(CompanyRecord):
    actor_email = models.EmailField()
    resource = models.CharField(max_length=30)
    record_id = models.PositiveBigIntegerField()
    summary = models.CharField(max_length=400)


class Department(CompanyRecord):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta(CompanyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=("company", "name"), name="business_company_department")]


class Employee(CompanyRecord):
    """Work directory only; private HR/payroll data does not belong in this model."""
    name = models.CharField(max_length=200)
    employee_code = models.CharField(max_length=64)
    work_email = models.EmailField(blank=True)
    work_phone = models.CharField(max_length=50, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)

    class Meta(CompanyRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=("company", "employee_code"), name="business_company_employee_code"),
            models.UniqueConstraint(fields=("company", "user"), name="business_company_employee_user"),
        ]


class HelpdeskTicket(CompanyRecord):
    number = models.CharField(max_length=30)
    request_id = models.UUIDField(unique=True)
    payload_digest = models.CharField(max_length=64)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=10000)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.PROTECT)
    task = models.OneToOneField(Task, null=True, blank=True, on_delete=models.PROTECT, related_name="support_ticket")
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="support_tickets")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tickets")
    priority = models.CharField(max_length=10, default="normal", choices=[("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")])
    status = models.CharField(max_length=12, default="new", choices=[("new", "New"), ("in_progress", "In progress"), ("waiting", "Waiting"), ("resolved", "Resolved"), ("cancelled", "Cancelled")])
    due_date = models.DateField(null=True, blank=True)
    resolution = models.TextField(blank=True, max_length=2000)
    resolved_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta(CompanyRecord.Meta):
        constraints = [models.UniqueConstraint(fields=("company", "number"), name="business_company_ticket_number")]


class TicketMessage(models.Model):
    ticket = models.ForeignKey(HelpdeskTicket, on_delete=models.CASCADE, related_name="messages")
    request_id = models.UUIDField(unique=True)
    body = models.TextField(max_length=2000)
    kind = models.CharField(max_length=12, default="note", choices=[("note", "Note"), ("resolution", "Resolution")])
    actor_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-id",)


class TimesheetEntry(CompanyRecord):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="timesheets")
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="timesheets")
    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.PROTECT, related_name="timesheets")
    ticket = models.ForeignKey(HelpdeskTicket, null=True, blank=True, on_delete=models.PROTECT, related_name="timesheets")
    date = models.DateField(default=timezone.localdate)
    minutes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(1440)])
    description = models.CharField(max_length=300)
    status = models.CharField(max_length=12, default="draft", choices=[("draft", "Draft"), ("submitted", "Submitted"), ("approved", "Approved"), ("voided", "Voided")])
    request_id = models.UUIDField(unique=True)
    payload_digest = models.CharField(max_length=64)
    creator_email = models.EmailField()
    review_note = models.CharField(max_length=500, blank=True)
    reviewed_by = models.EmailField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta(CompanyRecord.Meta):
        indexes = [models.Index(fields=("company", "employee", "date"), name="business_timesheet_day")]
        constraints = [models.CheckConstraint(condition=models.Q(minutes__gte=1, minutes__lte=1440), name="business_timesheet_minutes")]
