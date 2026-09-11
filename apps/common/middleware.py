# apps/common/middleware.py

import logging
import time
import uuid

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """اضافه کردن request_id به هر درخواست"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response


class RequestTimingMiddleware:
    """زمان پاسخ هر درخواست رو لاگ می‌کنه"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start

        # ✅ فقط درخواست‌های API
        if request.path.startswith("/api/"):
            duration_ms = duration * 1000

            if duration > 0.5:  # > 500ms
                logger.warning(
                    f"🐌 SLOW: {request.method} {request.path} "
                    f"→ {response.status_code} in {duration_ms:.0f}ms"
                )
            elif duration > 0.1:  # > 100ms
                logger.info(
                    f"⏱️ {request.method} {request.path} "
                    f"→ {response.status_code} in {duration_ms:.0f}ms"
                )
            else:
                logger.debug(
                    f"⚡ {request.method} {request.path} "
                    f"→ {response.status_code} in {duration_ms:.0f}ms"
                )

        return response