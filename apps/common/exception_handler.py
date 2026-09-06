from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.common")


def custom_exception_handler(exc, context):
    """فرمت پاسخ خطاها را استاندارد می‌کند و از افشای Traceback به کاربر جلوگیری می‌کند."""
    response = exception_handler(exc, context)
    request = context.get("request")
    request_id = getattr(request, "request_id", "unknown") if request else "unknown"

    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(detail="دسترسی مجاز نیست.")

    if response is not None:
        response.data = {
            "success": False,
            "error": {
                "code": getattr(exc, "default_code", "ERROR"),
                "message": response.data.get("detail") or response.data.get("non_field_errors") or "درخواست نامعتبر است.",
                "request_id": request_id,
            },
        }
        if hasattr(response.data["error"], "get"):
            if "detail" in response.data["error"]:
                response.data["error"]["message"] = response.data["error"].get("detail")
        return response

    logger.exception("unhandled_exception", extra={"request_id": request_id, "path": getattr(request, "path", None)})
    return Response(
        {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "خطایی در سرور رخ داده است. لطفاً دوباره تلاش کنید.",
                "request_id": request_id,
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# اگر ValidationError یا PermissionError از نوع DRF نباشد، این Handler هم آن‌ها را می‌گیرد.
def handle_validation_error(request, exc):
    return Response(
        {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "request_id": getattr(request, "request_id", "unknown"),
            },
        },
        status=status.HTTP_400_BAD_REQUEST,
    )
