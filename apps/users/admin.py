"""
تنظیمات Django Admin برای مدل User.

فیلدهای مالی/حساس (is_superuser، date_joined، last_login) به‌صورت
read_only در نظر گرفته می‌شوند تا از تغییر تصادفی یا سوءاستفاده از طریق
Admin توسط یک staff غیرمجاز جلوگیری شود.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "is_active", "is_staff", "is_email_verified", "date_joined"]
    list_filter = ["is_active", "is_staff", "is_email_verified"]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    readonly_fields = ["date_joined", "last_login"]

    # UserAdmin پیش‌فرض Django براساس فیلد username ساخته شده؛ چون این
    # پروژه username ندارد، fieldsets و add_fieldsets باید کامل بازنویسی
    # شوند وگرنه Admin با خطای «username field not found» مواجه می‌شود.
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "phone_number",
                    "is_staff",
                    "is_active",
                )
            },
        ),
    )
