import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from recipes.models import RecipeReview


def test_used_ingredient_cant_be_deleted(recipe, ingredient):
    with pytest.raises(ProtectedError):
        ingredient.delete()


def test_admin_reviews_recipe_only_once(recipe, admin):
    RecipeReview.objects.create(recipe=recipe, author=admin, rating=8)

    with pytest.raises(IntegrityError):
        RecipeReview.objects.create(recipe=recipe, author=admin, rating=3)
