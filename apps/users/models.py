"""
Custom User Model.

چرا از ابتدا Custom User؟ چون تغییر AUTH_USER_MODEL بعد از migration واقعی
عملاً غیرممکن است. این یکی از معروف‌ترین توصیه‌های Django است.
"""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from apps.common.models import TimeStampedModel
from .managers import UserManager
from .utils import normalize_phone_number
from .managers import UserManager



def normalize_phone_number(phone: str) -> str:
    """
    تبدیل شماره موبایل به فرمت استاندارد E.164 (+98...)
    مثال‌های قابل قبول:
        09036610574
        9036610574
        +989036610574
        989036610574
    خروجی همیشه: +989036610574
    """
    if not phone:
        return phone

    phone = phone.strip().replace(" ", "").replace("-", "")

    if phone.startswith("+98"):
        return phone
    if phone.startswith("98") and len(phone) == 12:
        return f"+{phone}"
    if phone.startswith("0") and len(phone) == 11:
        return f"+98{phone[1:]}"
    if phone.startswith("9") and len(phone) == 10:
        return f"+98{phone}"

    return phone


phone_number_validator = RegexValidator(
    regex=r"^(\+98|0)?9\d{9}$",
    message="شماره موبایل معتبر نیست. مثال‌های صحیح: 09036610574 یا +989036610574",
)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    شناسه ورود: شماره موبایل
    فیلدهای اجباری شروع: phone_number + name + password
    """

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        validators=[phone_number_validator],
        help_text="شماره موبایل به فرمت بین‌المللی (مثال: +989036610574)",
    )

    first_name = models.CharField(
    max_length=100,
    help_text="نام کاربر",
)

    last_name = models.CharField(
        max_length=100,
        help_text="نام خانوادگی کاربر",
    )

    # ایمیل اختیاری نگه داشته شده تا بعداً بدون دردسر اضافه شود
    email = models.EmailField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["first_name" , "last_name"]

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["is_active", "date_joined"]),
            models.Index(fields=["phone_number"]),
        ]

    def __str__(self) -> str:
        return self.phone_number

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # همیشه قبل از ذخیره نرمال‌سازی کن
        if self.phone_number:
            self.phone_number = normalize_phone_number(self.phone_number)
        super().save(*args, **kwargs)