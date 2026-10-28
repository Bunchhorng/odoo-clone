from django.urls import path

from . import views

app_name = "companies"
urlpatterns = [
    path("", views.companies, name="list"),
    path("<int:company_id>/select/", views.select_company, name="select"),
    path("<int:company_id>/members/", views.members, name="members"),
    path("<int:company_id>/members/<int:member_id>/", views.update_member, name="member"),
]
