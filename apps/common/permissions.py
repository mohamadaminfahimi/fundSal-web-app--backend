from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """برای داده‌های مالی فقط مالک یا مدیر می‌تواند دسترسی داشته باشد."""

    def has_object_permission(self, request, view, obj):
        return bool(request.user and (request.user.is_staff or getattr(obj, "user_id", None) == request.user.id))


class IsEmailVerified(BasePermission):
    """برای انجام تراکنش‌های مالی، کاربر باید ایمیل خودش را تأیید کرده باشد."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_email_verified)
