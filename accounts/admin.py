from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Status", {"fields": ("is_active", "approved_at", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("username", "email", "password1", "password2")}),)
    list_display = ("username", "email", "is_active", "approved_at", "is_superuser", "date_joined")
    list_filter = ("is_active", "is_superuser")
    search_fields = ("username", "email")
    ordering = ("date_joined",)
