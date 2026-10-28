from django.contrib import admin

from .models import Activity, Contact, Invoice, Opportunity, Order, Payment, Product, ProductCategory, Project, StockMovement, Task


class BusinessReadOnlyAdmin(admin.ModelAdmin):
    """Business writes go through transactional APIs, including for staff users."""
    list_per_page = 30

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in (Activity, Contact, Invoice, Opportunity, Order, Payment, Product, ProductCategory, Project, StockMovement, Task):
    admin.site.register(model, BusinessReadOnlyAdmin)
