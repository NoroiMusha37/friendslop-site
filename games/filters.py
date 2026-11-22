import django_filters
from django.db.models import Exists, OuterRef

from accounts.models import User
from common.filters import RatingOrderingFilter
from games.models import Game, GameCategory, GameStatus, Genre, PlayStatus


class GameFilter(django_filters.FilterSet):
    genre = django_filters.ModelChoiceFilter(
        field_name="genres",
        queryset=Genre.objects.all(),
    )
    category = django_filters.ChoiceFilter(
        choices=GameCategory.choices,
        method="filter_category",
    )
    status = django_filters.ChoiceFilter(
        choices=PlayStatus.choices,
        method="applied_together",
    )
    admin = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(is_superuser=True),
        to_field_name="username",
        method="applied_together",
    )
    search = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )
    ordering = RatingOrderingFilter(rating_fields=("combined_rating", "rawg_rating"))

    class Meta:
        model = Game
        fields = ["genre", "category", "status", "admin", "search", "ordering"]

    @staticmethod
    def filter_category(queryset, name, value):
        return queryset.filter(categories__contains=[value])

    @staticmethod
    def applied_together(queryset, name, value: str):
        return queryset  # `filter_queryset` handles these, because both must match the same status row

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        status = self.form.cleaned_data.get("status")
        admin = self.form.cleaned_data.get("admin")
        if not status and not admin:
            return queryset
        statuses = GameStatus.objects.filter(game=OuterRef("pk"))
        if status:
            statuses = statuses.filter(status=status)
        if admin:
            statuses = statuses.filter(user=admin)
        return queryset.filter(Exists(statuses))
