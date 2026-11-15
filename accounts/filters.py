import django_filters

from accounts.models import User


class UserFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(
        choices=[("pending", "Pending"), ("active", "Active"), ("banned", "Banned")],
        method="filter_status",
    )

    class Meta:
        model = User
        fields = ["status"]

    @staticmethod
    def filter_status(queryset, name, value):
        if value == "pending":
            return queryset.filter(approved_at__isnull=True)
        return queryset.filter(approved_at__isnull=False, is_active=value == "active")
