from django.apps import AppConfig


class CommonConfig(AppConfig):
    """
    اپ common محل نگهداری کدهای مشترک بین سایر اپ‌هاست: کلاس‌های پایه‌ی
    Model (مثل TimeStampedModel)، Exception Handler سراسری، Permission های
    عمومی و مواردی از این دست که نباید در هیچ اپ Domain-specific دیگری
    تکرار شوند (اصل DRY).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "Common"
