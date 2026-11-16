import django_filters
from django.db.models import Case, IntegerField, Q, Value, When
from django.db.models.functions import Length

from common.filters import RatingOrderingFilter
from recipes.models import CookingMethod, Ingredient, Recipe

MIN_SEARCH_LENGTH = 2
MAX_SEARCH_RESULTS = 20


class RecipeFilter(django_filters.FilterSet):
    cooking_method = django_filters.ChoiceFilter(choices=CookingMethod.choices)
    ingredient = django_filters.ModelChoiceFilter(
        field_name="ingredients",
        queryset=Ingredient.objects.all(),
    )
    search = django_filters.CharFilter(method="filter_search")
    ordering = RatingOrderingFilter()

    class Meta:
        model = Recipe
        fields = ["cooking_method", "ingredient", "search", "ordering"]

    @staticmethod
    def filter_search(queryset, name, value):
        # Title matches come before matches found only in the instructions
        return queryset.filter(Q(title__icontains=value) | Q(instructions__icontains=value)).annotate(
            search_priority=Case(
                When(title__icontains=value, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )


class IngredientFilter(django_filters.FilterSet):
    """Type-ahead search: names containing the text, those starting with it first, shorter names first."""

    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Ingredient
        fields = ["search"]

    def filter_queryset(self, queryset):
        # Too short or missing text gives nothing instead of every ingredient
        if len(self.form.cleaned_data.get("search") or "") < MIN_SEARCH_LENGTH:
            return queryset.none()
        return super().filter_queryset(queryset)

    @staticmethod
    def filter_search(queryset, name, value):
        starts_first = Case(
            When(name__istartswith=value, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
        return queryset.filter(name__icontains=value).order_by(
            starts_first,
            Length("name"),
            "name",
        )[:MAX_SEARCH_RESULTS]
