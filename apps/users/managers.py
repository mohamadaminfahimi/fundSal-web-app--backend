"""
Manager سفارشی برای User مبتنی بر ایمیل.

Django به‌طور پیش‌فرض انتظار دارد User یک فیلد username داشته باشد. چون در
این پروژه ایمیل به‌عنوان شناسه‌ی یکتای ورود استفاده می‌شود (رایج‌تر و
کاربرپسندتر از username برای یک اپلیکیشن مالی)، باید متدهای create_user و
create_superuser به‌صورت دستی بازنویسی شوند.
"""

from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    def _create_user(
        self,
        email: str,
        password: str | None,
        first_name: str = "",
        phone_number: str = "",
        **extra_fields,
    ):
        if not email:
            raise ValueError("Users must have an email address.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            first_name=first_name,
            phone_number=phone_number,
            **extra_fields,
        )

        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)

        return user

    def create_user(
        self,
        email: str,
        password: str | None = None,
        first_name: str = "",
        phone_number: str = "",
        **extra_fields,
    ):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", False)

        if not email:
            raise ValueError("Users must have an email address.")

        return self._create_user(
            email=email,
            password=password,
            first_name=first_name,
            phone_number=phone_number,
            **extra_fields,
        )

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        first_name: str = "",
        phone_number: str = "",
        **extra_fields,
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")

        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(
            email=email,
            password=password,
            first_name=first_name,
            phone_number=phone_number,
            **extra_fields,
        )