from datetime import timedelta
from math import ceil

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.core.api import APIError
from .models import AuthRateBucket


def bucket_key(purpose, identity):
    return salted_hmac("kerp.auth.throttle", f"{purpose}\0{identity}", algorithm="sha256").hexdigest()


def consume_limits(limits):
    """Count attempts atomically before expensive authentication or queued delivery."""
    now = timezone.now()
    window = settings.AUTH_RATE_WINDOW_SECONDS
    entries = sorted((bucket_key(purpose, identity), limit) for purpose, identity, limit in limits)
    with transaction.atomic():
        buckets = []
        for key, limit in entries:
            bucket, _ = AuthRateBucket.objects.select_for_update().get_or_create(
                key=key, defaults={"expires_at": now + timedelta(seconds=window)},
            )
            if bucket.expires_at <= now:
                bucket.count = 0
                bucket.expires_at = now + timedelta(seconds=window)
            if bucket.count >= limit:
                wait = max(1, ceil((bucket.expires_at - now).total_seconds()))
                raise APIError("Too many attempts. Please wait before trying again.", 429,
                               headers={"Retry-After": str(wait)})
            buckets.append(bucket)
        for bucket in buckets:
            bucket.count += 1
            bucket.save(update_fields=["count", "expires_at"])


def request_ip(request):
    # Forwarded headers are untrusted until an explicit trusted-proxy policy exists.
    return request.META.get("REMOTE_ADDR", "unknown")


def clear_login_limit(email):
    AuthRateBucket.objects.filter(key=bucket_key("login:identity", email.casefold())).delete()
