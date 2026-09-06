import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("apps.common")


class RequestIDMiddleware(MiddlewareMixin):
    """برای هر درخواست یک request_id منحصر به فرد می‌سازد تا ردیابی مالی و خطاها ساده‌تر شود."""

    def process_request(self, request):
        request.request_id = str(uuid.uuid4())
        request.start_time = time.perf_counter()

    def process_response(self, request, response):
        duration_ms = round((time.perf_counter() - getattr(request, "start_time", time.perf_counter())) * 1000, 2)
        request_id = getattr(request, "request_id", "unknown")
        response["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": getattr(request.user, "id", None),
            },
        )
        return response

    def process_exception(self, request, exception):
        request_id = getattr(request, "request_id", "unknown")
        logger.exception(
            "request_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "user_id": getattr(request.user, "id", None),
                "exception_type": type(exception).__name__,
            },
        )
