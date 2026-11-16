import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from accounts.models import User
from conftest import PASSWORD
from recipes.models import Ingredient, Recipe


@pytest.fixture(autouse=True)
def media_in_tmp(settings, tmp_path):
    # Uploaded files go to a temporary folder instead of the project's media/
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def friend(db):
    return User.objects.create_superuser(
        "friend",
        "friend@example.com",
        PASSWORD,
    )


@pytest.fixture
def ingredient(db):
    return Ingredient.objects.create(name="tomato")


@pytest.fixture
def recipe(ingredient):
    recipe = Recipe.objects.create(
        title="Salad",
        instructions="Chop 2 tomatoes.",
        cooking_method="RAW",
    )
    recipe.ingredients.add(ingredient)
    return recipe


def image_file(name="cover.png", size=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size).save(buffer, "PNG")
    return SimpleUploadedFile(
        name,
        buffer.getvalue(),
        content_type="image/png",
    )
