"""
URL Configuration اصلی پروژه.

مسیرهای API نسخه‌بندی شده هستند (/api/v1/) تا در آینده بتوان نسخه‌ی جدید
API را بدون شکستن کلاینت‌های فعلی (frontend، اپ موبایل و غیره) اضافه کرد.
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

from apps.common.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/wallet/", include("apps.wallet.urls")),
    path("api/v1/transactions/", include("apps.transactions.urls")),
    path("api/v1/trading/", include("apps.trading.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
