from accounts.models import User


class AdminOwnerInline:
    """For rows only an admin can own: the owner dropdown offers admins only."""

    owner_field = "author"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == self.owner_field:
            kwargs["queryset"] = User.objects.filter(is_superuser=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
