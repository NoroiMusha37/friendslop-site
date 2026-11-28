import django_filters
from django_filters.rest_framework import BooleanFilter
from rest_framework.exceptions import PermissionDenied

from common.filters import RatingOrderingFilter
from exercises.models import Exercise, LoadCategory, MuscleCategory, TrainingPlan


class ExerciseFilter(django_filters.FilterSet):
    muscle = django_filters.ChoiceFilter(
        choices=MuscleCategory.choices,
        method="filter_muscle",
    )
    load = django_filters.ChoiceFilter(
        field_name="load_category",
        choices=LoadCategory.choices,
    )
    intensity = django_filters.NumberFilter()
    search = django_filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )
    archived = BooleanFilter(method="applied_later", help_text="`true` lists archived exercises (admins only)")
    ordering = RatingOrderingFilter()

    class Meta:
        model = Exercise
        fields = ["muscle", "load", "intensity", "search", "archived", "ordering"]

    @staticmethod
    def filter_muscle(queryset, name, value):
        return queryset.filter(muscle_categories__contains=[value])

    @staticmethod
    def applied_later(queryset, name, value):
        return queryset  # `filter_queryset` handles it, because leaving it out must also filter

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        archived = bool(self.form.cleaned_data.get("archived"))
        if archived and not self.request.user.is_superuser:
            raise PermissionDenied
        return queryset.filter(archived_at__isnull=not archived)


class TrainingPlanFilter(django_filters.FilterSet):
    history = BooleanFilter(method="applied_later", help_text="`true` also lists plans that were edited into new ones")
    favourite = BooleanFilter(method="filter_favourite", help_text="the logged-in admin's favourites")

    class Meta:
        model = TrainingPlan
        fields = ["history", "favourite"]

    @staticmethod
    def applied_later(queryset, name, value):
        return queryset  # `filter_queryset` handles it, because leaving it out must also filter

    @staticmethod
    def filter_favourite(queryset, name, value):
        return queryset.filter(is_favourite=value)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        # A favourited plan stays findable after it is edited, even though it is no longer the latest version
        if self.form.cleaned_data.get("history") or self.form.cleaned_data.get("favourite"):
            return queryset
        return queryset.filter(copies__isnull=True)
