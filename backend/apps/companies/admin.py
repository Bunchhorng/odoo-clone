from django.contrib import admin

from .models import Company, CompanyMembership


class MembershipInline(admin.TabularInline):
    model = CompanyMembership
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (MembershipInline,)


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_active")
    list_filter = ("role", "is_active", "company")
    search_fields = ("user__email", "company__name")
    autocomplete_fields = ("user", "company")
    list_select_related = ("user", "company")
