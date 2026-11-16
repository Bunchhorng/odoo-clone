from django.conf import settings
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name


class CompanyMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Administrator"
        MEMBER = "member", "Member"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("company", "user"), name="unique_company_membership")
        ]

    def __str__(self):
        return f"{self.user} at {self.company}"


class CompanyAccessGroup(models.Model):
    """Company-scoped access group, inspired by ERP role groups."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="access_groups")
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=64)
    # Stable ID for built-in groups. Names and codes can be renamed safely.
    system_key = models.SlugField(max_length=64, null=True, blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("company", "code"), name="companies_access_group_code"),
            models.UniqueConstraint(fields=("company", "system_key"), name="companies_access_group_system_key"),
        ]
        ordering = ("name", "id")


class CompanyAccessGroupMembership(models.Model):
    group = models.ForeignKey(CompanyAccessGroup, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_access_groups")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("group", "user"), name="companies_access_group_member")]


class AppAccessRight(models.Model):
    """Additive CRUD/approve grants for one application group."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="app_access_rights")
    group = models.ForeignKey(CompanyAccessGroup, on_delete=models.CASCADE, related_name="app_access_rights")
    app_key = models.SlugField(max_length=64)
    can_read = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_write = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("company", "group", "app_key"), name="companies_app_access_right")]

    def clean(self):
        if self.group_id and self.company_id and self.group.company_id != self.company_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("The access group must belong to the same company.")


class UserAppAccessOverride(models.Model):
    """Tri-state user override. False revokes and always wins over group grants."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="user_app_access_overrides")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="app_access_overrides")
    app_key = models.SlugField(max_length=64)
    can_read = models.BooleanField(null=True, blank=True)
    can_create = models.BooleanField(null=True, blank=True)
    can_write = models.BooleanField(null=True, blank=True)
    can_delete = models.BooleanField(null=True, blank=True)
    can_approve = models.BooleanField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("company", "user", "app_key"), name="companies_user_app_override")]


class AppRecordRule(models.Model):
    class Scope(models.TextChoices):
        ALL_COMPANY = "all_company", "All company records"
        OWN = "own", "Own records"
        ASSIGNED = "assigned", "Assigned records"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="app_record_rules")
    group = models.ForeignKey(CompanyAccessGroup, on_delete=models.CASCADE, related_name="record_rules")
    app_key = models.SlugField(max_length=64)
    # Dotted identifiers (for example ``business.helpdeskticket``) keep the
    # rule definition independent from Python imports while remaining stable.
    model_key = models.CharField(max_length=100)
    scope = models.CharField(max_length=20, choices=Scope.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("company", "group", "app_key", "model_key", "scope"), name="companies_app_record_rule")]

    def clean(self):
        from django.core.exceptions import ValidationError
        from .permissions import record_scope_supported
        if self.group_id and self.company_id and self.group.company_id != self.company_id:
            raise ValidationError("The access group must belong to the same company.")
        if not record_scope_supported(self.app_key, self.model_key, self.scope):
            raise ValidationError({"scope": f"{self.scope} is not supported for {self.model_key}; use all_company."})
