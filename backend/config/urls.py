from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Odoo Project Administration"
admin.site.site_title = "Odoo Project"
admin.site.index_title = "Workspace administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/companies/", include("apps.companies.urls")),
    path("api/v1/companies/<int:company_id>/erp/", include("apps.business.urls")),
    path("api/v1/", include("apps.core.urls")),
]
