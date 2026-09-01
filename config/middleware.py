import logging
import re
import uuid

from .logging import request_id_context


logger = logging.getLogger("crm.requests")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else uuid.uuid4().hex
        request.request_id = request_id
        token = request_id_context.set(request_id)
        try:
            response = self.get_response(request)
        except Exception:
            logger.exception(
                "Unhandled request error method=%s path=%s user_id=%s",
                request.method,
                request.path,
                request.user.pk if getattr(request, "user", None) and request.user.is_authenticated else "-",
            )
            raise
        finally:
            request_id_context.reset(token)
        response["X-Request-ID"] = request_id
        return response
