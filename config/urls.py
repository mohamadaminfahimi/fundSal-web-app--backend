"""
URL Configuration اصلی پروژه.

مسیرهای API نسخه‌بندی شده هستند (/api/v1/) تا در آینده بتوان نسخه‌ی جدید
API را بدون شکستن کلاینت‌های فعلی (frontend، اپ موبایل و غیره) اضافه کرد.
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
]

# ✅ debug-toolbar فقط در حالت DEBUG
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns