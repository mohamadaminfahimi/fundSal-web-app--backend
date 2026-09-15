"""
Manager سفارشی برای User مبتنی بر شماره موبایل.
"""

from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager

from .utils import normalize_phone_number


class UserManager(BaseUserManager):
    """
    Manager سفارشی مدل User.

    شناسه ورود:
        phone_number

    اطلاعات نام:
        first_name
        last_name
    """

    def _create_user(
        self,
        phone_number: str,
        password: str | None,
        first_name: str,
        last_name: str,
        **extra_fields,
    ):
        if not phone_number:
            raise ValueError("شماره موبایل الزامی است.")

        if not first_name:
            raise ValueError("نام الزامی است.")

        if not last_name:
            raise ValueError("نام خانوادگی الزامی است.")

        phone_number = normalize_phone_number(phone_number)

        user = self.model(
            phone_number=phone_number,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            **extra_fields,
        )

        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)

        return user

    def create_user(
        self,
        phone_number: str,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        **extra_fields,
    ):
        """
        ایجاد کاربر معمولی.
        """

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", False)

        return self._create_user(
            phone_number=phone_number,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )

    def create_superuser(
        self,
        phone_number: str,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        **extra_fields,
    ):
        """
        ایجاد کاربر Superuser.
        """

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_email_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(
            phone_number=phone_number,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )
