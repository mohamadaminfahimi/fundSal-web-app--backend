# apps/admin_api/permissions.py

from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    فقط کاربران با is_staff=True می‌تونن دسترسی داشته باشن.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.is_staff
        )