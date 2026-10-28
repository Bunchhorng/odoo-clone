from decimal import Decimal

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


class StockMovement(CompanyRecord):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    reason = models.CharField(max_length=300)
    actor_email = models.EmailField()


class Invoice(CompanyRecord):
    kind = models.CharField(max_length=10, choices=[("customer", "Customer Invoice"), ("vendor", "Vendor Bill")])
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
