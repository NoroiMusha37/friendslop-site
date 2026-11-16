import django_filters
from django.db.models import Case, IntegerField, Q, Value, When

from common.filters import RatingOrderingFilter
from recipes.models import CookingMethod, Ingredient, Recipe


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
