from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Admins are superusers (DRF's built-in IsAdminUser checks is_staff instead)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
