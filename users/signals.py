import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver


logger = logging.getLogger("crm.security")


def _client_ip(request):
    if request is None:
        return "-"
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "-")


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    logger.info("login_success user_id=%s ip=%s", user.pk, _client_ip(request))


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    logger.info("logout user_id=%s ip=%s", getattr(user, "pk", "-"), _client_ip(request))


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    logger.warning("login_failed ip=%s", _client_ip(request))
