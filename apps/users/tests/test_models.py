"""
تست‌های مدل User و UserManager.

این تست‌ها روی دیتابیس واقعی (PostgreSQL تعریف‌شده در .env) اجرا می‌شوند؛
pytest-django به‌ازای هر Test Run یک دیتابیس تست جدا (test_<POSTGRES_DB>)
می‌سازد تا داده‌های واقعی dev دستکاری نشوند.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.users.models import User

pytestmark = pytest.mark.django_db


class TestUserManager:
    def test_create_user_sets_expected_defaults(self):
        user = User.objects.create_user(email="user@example.com", password="StrongPass123!")

        assert user.email == "user@example.com"
        assert user.check_password("StrongPass123!")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="whatever")

    def test_email_is_normalized(self):
        user = User.objects.create_user(email="User@EXAMPLE.com", password="StrongPass123!")

        # normalize_email فقط دامنه را lower-case می‌کند، نه local-part را؛
        # این رفتار استاندارد Django است.
        assert user.email == "User@example.com"

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(email="dup@example.com", password="StrongPass123!")

        with pytest.raises(ValidationError):
            User.objects.create_user(email="dup@example.com", password="AnotherPass123!")

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="AdminPass123!")

        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_rejects_is_staff_false(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="admin2@example.com", password="AdminPass123!", is_staff=False
            )

    def test_create_superuser_rejects_is_superuser_false(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="admin3@example.com", password="AdminPass123!", is_superuser=False
            )


class TestUserModel:
    def test_full_name_property(self):
        user = User.objects.create_user(
            email="ali@example.com",
            password="StrongPass123!",
            first_name="Ali",
            last_name="Rezaei",
        )

        assert user.full_name == "Ali Rezaei"

    def test_str_returns_email(self):
        user = User.objects.create_user(email="ali@example.com", password="StrongPass123!")

        assert str(user) == "ali@example.com"

    def test_invalid_phone_number_is_rejected(self):
        user = User(email="bad-phone@example.com", phone_number="not-a-phone")
        user.set_password("StrongPass123!")

        with pytest.raises(ValidationError):
            user.full_clean()
