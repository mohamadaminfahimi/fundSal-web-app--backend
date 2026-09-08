"""
Custom User Model.

چرا از ابتدا (Phase 4) یک Custom User می‌سازیم و نه بعداً؟ چون تغییر
AUTH_USER_MODEL بعد از این‌که Migration های واقعی روی دیتابیس اجرا شدند
عملاً غیرممکن است بدون بازنویسی دستی و پرخطر Migration ها. این یکی از
معروف‌ترین توصیه‌های خود مستندات Django است: همیشه از ابتدای پروژه یک
Custom User تعریف کنید، حتی اگر فعلاً تفاوت زیادی با User پیش‌فرض نداشته
باشد.
"""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from apps.common.models import TimeStampedModel

from .managers import UserManager

# اعتبارسنجی شماره تلفن به فرمت بین‌المللی (E.164)؛ این فرمت به‌طور یکتا
# کشور را هم مشخص می‌کند و مانع ثبت مقادیر غیرقابل‌اعتماد می‌شود.
phone_number_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{7,14}$",
    message="Phone number must be entered in international format, e.g. '+989121234567'.",
)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    برخلاف User پیش‌فرض Django، شناسه‌ی ورود این مدل email است، نه username.
    دلیل: در یک اپلیکیشن مالی، ایمیل هم برای ورود و هم برای اطلاع‌رسانی‌های
    حساس (تغییر رمز، هشدار برداشت، فاکتور) استفاده می‌شود؛ نگه‌داشتن یک
    username جدا و بی‌ارتباط با ایمیل فقط پیچیدگی اضافه می‌کند.
    """

    email = models.EmailField(unique=True, db_index=True)

    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")

    phone_number = models.CharField(
        max_length=20,
        validators=[phone_number_validator],
        null=False,
        blank=False,
        unique=True,
        help_text="Optional, international format (e.g. +989121234567).",
    )

    # is_active به‌جای حذف فیزیکی کاربر استفاده می‌شود (Soft Disable)؛ چون
    # این کاربر ممکن است سابقه‌ی تراکنش مالی داشته باشد که هرگز نباید از
    # طریق حذف Cascade از بین برود.
    is_active = models.BooleanField(default=True)

    # is_staff دسترسی به Django Admin را کنترل می‌کند (جدا از is_superuser
    # که دسترسی کامل به تمام Permission ها می‌دهد).
    is_staff = models.BooleanField(default=False)

    # is_email_verified قبل از تأیید ایمیل، اجازه‌ی انجام عملیات مالی
    # (خرید/فروش/برداشت) را نمی‌دهد؛ منطق دقیق آن در Permission های
    # Phase 6 (Authorization) اعمال می‌شود، نه اینجا.
    is_email_verified = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        # ایندکس مرکب برای Query های رایج در Django Admin و پنل پشتیبانی
        # («کاربران فعال را بر اساس تاریخ عضویت مرتب کن»).
        indexes = [
            models.Index(fields=["is_active", "date_joined"]),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
