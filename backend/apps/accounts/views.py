from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import ensure_csrf_cookie

from apps.companies.access import company_data, memberships_for
from apps.core.api import APIError, api, json_body, text_field
from .models import PasswordResetDelivery
from .security import clear_login_limit, consume_limits, request_ip


def password_fields(data, *names):
    for name in names:
        value = data.get(name)
        if not isinstance(value, str) or not value or len(value) > 1024:
            raise APIError("Complete all password fields with at most 1024 characters each.")


def validate_form(form):
    if not form.is_valid():
        raise APIError(" ".join(str(message) for messages in form.errors.values() for message in messages))


def session_data(request):
    if not request.user.is_authenticated:
        return {"user": None, "companies": [], "active_company_id": None}
    companies = [company_data(item) for item in memberships_for(request.user)]
    company_ids = [company["id"] for company in companies]
    selected = request.session.get("active_company_id")
    if selected not in company_ids:
        selected = company_ids[0] if company_ids else None
        request.session["active_company_id"] = selected
    return {
        "user": {
            "id": request.user.pk,
            "email": request.user.email,
            "name": request.user.get_full_name() or request.user.email,
            "is_staff": request.user.is_staff,
        },
        "companies": companies,
        "active_company_id": selected,
    }


@ensure_csrf_cookie
@api(["GET"], authenticated=False)
def session(request):
    return JsonResponse(session_data(request))


@api(["POST"], authenticated=False)
def sign_in(request):
    data = json_body(request, {"email", "password"})
    email = get_user_model().objects.normalize_email(text_field(data, "email", maximum=254))
    # Passwords must retain spaces, unlike ordinary text fields.
    password = data.get("password")
    if not isinstance(password, str) or not password or len(password) > 1024:
        raise APIError("Enter your email and password.")
    # Use the stored identity when database collation treats alternate spellings
    # as equivalent (e.g. accent-insensitive MySQL comparisons).
    canonical = get_user_model().objects.filter(email__iexact=email).values_list("email", flat=True).first() or email
    consume_limits([
        ("login:identity", canonical.casefold(), settings.AUTH_LOGIN_IDENTITY_LIMIT),
        ("login:ip", request_ip(request), settings.AUTH_LOGIN_IP_LIMIT),
    ])
    user = authenticate(request, email=email, password=password)
    if user is None:
        raise APIError("Email or password is incorrect.", 401)
    login(request, user)
    clear_login_limit(user.email)
    return JsonResponse(session_data(request))


@api(["POST"], authenticated=False)
def sign_up(request):
    data = json_body(request, {"email", "password", "password_confirmation"})
    email = get_user_model().objects.normalize_email(text_field(data, "email", maximum=254))
    validate_email(email)
    password_fields(data, "password", "password_confirmation")
    if data["password"] != data["password_confirmation"]:
        raise APIError("Passwords do not match.")
    consume_limits([
        ("register:identity", email.casefold(), settings.AUTH_REGISTER_IDENTITY_LIMIT),
        ("register:ip", request_ip(request), settings.AUTH_REGISTER_IP_LIMIT),
    ])
    with transaction.atomic():
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise APIError("An account with this email already exists.", 409)
        user = User(email=email, is_active=True)
        validate_password(data["password"], user)
        user.set_password(data["password"])
        user.save()
    login(request, user)
    clear_login_limit(user.email)
    return JsonResponse(session_data(request), status=201)


@api(["POST"])
def sign_out(request):
    logout(request)
    return JsonResponse(session_data(request))


@api(["POST"])
def change_password(request):
    data = json_body(request, {"old_password", "new_password1", "new_password2"})
    password_fields(data, "old_password", "new_password1", "new_password2")
    consume_limits([("change-password:user", request.user.pk, 5)])
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        if not user.is_active:
            raise APIError("Please sign in.", 401)
        form = PasswordChangeForm(user, data)
        validate_form(form)
        form.save()
        update_session_auth_hash(request, user)
    clear_login_limit(user.email)
    return JsonResponse({"message": "Password changed. Other sessions will need to sign in again."})


@api(["POST"], authenticated=False)
def request_password_reset(request):
    data = json_body(request, {"email"})
    email = text_field(data, "email", maximum=254)
    validate_email(email)
    consume_limits([
        ("reset:identity", email.casefold(), settings.AUTH_RESET_IDENTITY_LIMIT),
        ("reset:ip", request_ip(request), settings.AUTH_RESET_IP_LIMIT),
    ])
    # Queue both known and unknown addresses; the HTTP path never looks up accounts
    # or contacts SMTP, keeping account eligibility out of its response behavior.
    PasswordResetDelivery.objects.create(email=email)
    return JsonResponse({"message": "If an eligible account exists, a password reset link will be sent."})


@api(["POST"], authenticated=False)
def confirm_password_reset(request):
    data = json_body(request, {"uid", "token", "new_password1", "new_password2"})
    uid = text_field(data, "uid", maximum=64)
    token = text_field(data, "token", maximum=256)
    password_fields(data, "new_password1", "new_password2")
    consume_limits([("reset-confirm:ip", request_ip(request), settings.AUTH_LOGIN_IP_LIMIT)])
    try:
        decoded = urlsafe_base64_decode(uid).decode("ascii")
        if not decoded.isdecimal() or len(decoded) > 19 or not 0 < int(decoded) <= 9223372036854775807:
            raise ValueError
        user_id = int(decoded)
    except (ValueError, UnicodeError, OverflowError):
        raise APIError("This password reset link is invalid or expired.") from None
    with transaction.atomic():
        user = get_user_model().objects.select_for_update().filter(pk=user_id, is_active=True).first()
        if user is None or not user.has_usable_password() or not default_token_generator.check_token(user, token):
            raise APIError("This password reset link is invalid or expired.")
        form = SetPasswordForm(user, data)
        validate_form(form)
        form.save()
        clear_login_limit(user.email)
    logout(request)
    return JsonResponse({"message": "Password reset. Sign in with your new password."})
