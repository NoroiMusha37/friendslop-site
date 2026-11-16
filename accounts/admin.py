from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts import services
from accounts.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Status",
            {"fields": ("is_active", "approved_at", "is_staff", "is_superuser")},
        ),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("username", "email", "password1", "password2")}),)
    list_display = (
        "username",
        "email",
        "is_active",
        "approved_at",
        "is_superuser",
        "date_joined",
    )
    list_filter = ("is_active", "is_superuser")
    search_fields = ("username", "email")
    ordering = ("date_joined",)

    # Status changes go through the actions below, so they follow the same rules as the API
    readonly_fields = ("is_active", "approved_at")
    actions = ["approve_users", "reject_users", "ban_users", "unban_users"]

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def _apply(self, request, queryset, change, done):
        changed = 0
        for user in queryset:
            try:
                change(user)
                changed += 1
            except services.UserStateError as e:
                self.message_user(
                    request,
                    f"{user.username}: {e}",
                    messages.WARNING,
                )
        if changed:
            self.message_user(
                request,
                f"{done} {changed} user(s).",
                messages.SUCCESS,
            )

    @admin.action(description="Approve selected users")
    def approve_users(self, request, queryset):
        self._apply(
            request,
            queryset,
            services.approve,
            "Approved",
        )

    @admin.action(description="Reject (delete) selected users")
    def reject_users(self, request, queryset):
        self._apply(
            request,
            queryset,
            services.reject,
            "Rejected",
        )

    @admin.action(description="Ban selected users")
    def ban_users(self, request, queryset):
        self._apply(
            request,
            queryset,
            services.ban,
            "Banned",
        )

    @admin.action(description="Unban selected users")
    def unban_users(self, request, queryset):
        self._apply(
            request,
            queryset,
            services.unban,
            "Unbanned",
        )
