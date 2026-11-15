import pytest

from recipes.models import Ingredient, Recipe


@pytest.fixture
def ingredient(db):
    return Ingredient.objects.create(name="tomato")


@pytest.fixture
def recipe(ingredient):
    recipe = Recipe.objects.create(title="Salad", instructions="Chop 2 tomatoes.", cooking_method="RAW")
    recipe.ingredients.add(ingredient)
    return recipe
