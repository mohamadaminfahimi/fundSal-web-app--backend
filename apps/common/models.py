"""
Model های پایه‌ی مشترک بین تمام اپ‌های پروژه.
"""

from django.db import models


class TimeStampedModel(models.Model):
    """
    فیلدهای created_at/updated_at در تقریباً هر Model مالی برای Audit و
    عیب‌یابی لازم هستند (مثلاً «این تراکنش دقیقاً چه زمانی ثبت شد؟»).
    این کلاس abstract است تا این دو فیلد در هر اپ به‌صورت جداگانه تکرار
    نشوند (اصل DRY).
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
