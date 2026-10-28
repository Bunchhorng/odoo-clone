import logging
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from apps.core.api import APIError

from .models import AuthRateBucket, PasswordResetDelivery
from .security import consume_limits

logger = logging.getLogger(__name__)


class QueuedPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        # The queue must see failures to retry. Django's default form logs/swallow
        # delivery failures, which would otherwise acknowledge a failed job.
        subject = "".join(render_to_string(subject_template_name, context).splitlines())
        body = render_to_string(email_template_name, context)
        message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name:
            message.attach_alternative(render_to_string(html_email_template_name, context), "text/html")
        message.send()


def process_next_delivery():
    """Deliver outside HTTP requests so account existence does not alter response work."""
    now = timezone.now()
    with transaction.atomic():
        job = PasswordResetDelivery.objects.select_for_update(skip_locked=True).filter(
            status=PasswordResetDelivery.Status.PENDING, next_attempt_at__lte=now,
        ).order_by("id").first()
        if job is None:
            return False
        if job.created_at < now - timedelta(seconds=settings.AUTH_RESET_QUEUE_TTL):
            job.status = PasswordResetDelivery.Status.FAILED
            job.processed_at = now
            job.save(update_fields=["status", "processed_at"])
            return True
        job.attempts += 1
        try:
            form = QueuedPasswordResetForm({"email": job.email})
            if form.is_valid():
                if job.attempts == 1:
                    # Resolve database-collation aliases only in the worker, so the
                    # public request path remains independent of account eligibility.
                    # Count a queued request once; transport retries keep its slot.
                    for user in form.get_users(job.email):
                        consume_limits([("reset-delivery:user", user.pk, settings.AUTH_RESET_IDENTITY_LIMIT)])
                origin = urlsplit(settings.FRONTEND_ORIGIN)
                form.save(
                    domain_override=origin.netloc, use_https=origin.scheme == "https",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    email_template_name="accounts/password_reset_email.txt",
                    subject_template_name="accounts/password_reset_subject.txt",
                    extra_email_context={"frontend_origin": settings.FRONTEND_ORIGIN},
                )
            job.status = PasswordResetDelivery.Status.DONE
            job.processed_at = now
        except APIError as exc:
            if exc.status != 429:
                raise
            job.status = PasswordResetDelivery.Status.DONE
            job.processed_at = now
        except Exception:
            # Never write reset tokens, credentials, recipients, or SMTP exceptions to logs.
            logger.warning("Password recovery delivery failed for request %s", job.pk)
            if job.attempts >= 3:
                job.status = PasswordResetDelivery.Status.FAILED
                job.processed_at = now
            else:
                job.next_attempt_at = now + timedelta(seconds=30 * job.attempts)
        job.save(update_fields=["status", "attempts", "next_attempt_at", "processed_at"])
    return True


def cleanup_transient_records():
    now = timezone.now()
    AuthRateBucket.objects.filter(expires_at__lt=now).delete()
    PasswordResetDelivery.objects.filter(processed_at__lt=now - timedelta(days=1)).delete()
