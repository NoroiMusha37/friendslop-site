import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from recipes.models import Ingredient, IngredientPair, RecipeReview


def test_pair_is_stored_only_with_smaller_id_first(ingredient):
    # The randomizer looks pairs up in this order, so a reversed copy would be a silent duplicate
    other = Ingredient.objects.create(name="basil")

    with pytest.raises(IntegrityError):
        IngredientPair.objects.create(ingredient_a=other, ingredient_b=ingredient, score=1.0)


def test_used_ingredient_cant_be_deleted(recipe, ingredient):
    with pytest.raises(ProtectedError):
        ingredient.delete()


def test_admin_reviews_recipe_only_once(recipe, admin):
    RecipeReview.objects.create(
        recipe=recipe,
        author=admin,
        rating=8,
    )

    with pytest.raises(IntegrityError):
        RecipeReview.objects.create(
            recipe=recipe,
            author=admin,
            rating=3,
        )
