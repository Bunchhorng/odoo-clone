from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "KERP Administration"
admin.site.site_title = "KERP"
admin.site.index_title = "Workspace administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
]
