import io
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from recipes.models import Recipe, RecipeImage, RecipeReview
from recipes.tests.conftest import image_file

LIST_URL = reverse("recipe-list")


def detail_url(recipe):
    return reverse("recipe-detail", args=[recipe.pk])


def titles(response):
    return [r["title"] for r in response.json()]


def make_recipe(title, instructions="Cook it."):
    return Recipe.objects.create(title=title, instructions=instructions, cooking_method="OTHER")


def test_regular_user_reads_but_cant_write(user_client, recipe):
    assert user_client.get(LIST_URL).status_code == 200
    assert user_client.get(detail_url(recipe)).status_code == 200
    assert user_client.post(LIST_URL, {}).status_code == 403
    assert user_client.patch(detail_url(recipe), {}).status_code == 403
    assert user_client.delete(detail_url(recipe)).status_code == 403


def test_editing_is_patch_only(admin_client, recipe):
    assert admin_client.put(detail_url(recipe), {}).status_code == 405


def test_admin_creates_recipe_with_cover(admin_client, ingredient):
    data = {
        "title": "Omelette",
        "instructions": "Beat 3 eggs.",
        "cooking_method": "FRIED",
        "ingredients": [ingredient.pk],
        "cover_image": image_file(),
    }

    response = admin_client.post(LIST_URL, data, format="multipart")

    assert response.status_code == 201
    body = response.json()
    assert body["ingredients"] == [{"id": ingredient.pk, "name": "tomato"}]
    assert os.path.exists(Recipe.objects.get(pk=body["id"]).cover_image.path)


def test_recipe_needs_an_ingredient(admin_client):
    data = {"title": "Air", "instructions": "-", "cooking_method": "RAW", "ingredients": []}

    response = admin_client.post(LIST_URL, data, format="json")

    assert response.status_code == 400
    assert "ingredients" in response.json()


def test_cover_over_5_mb_is_rejected(admin_client, recipe):
    # Random pixels don't compress, so this PNG is about 6 MB
    buffer = io.BytesIO()
    Image.frombytes("RGB", (1450, 1450), os.urandom(1450 * 1450 * 3)).save(buffer, "PNG")
    upload = SimpleUploadedFile("big.png", buffer.getvalue(), content_type="image/png")

    response = admin_client.patch(detail_url(recipe), {"cover_image": upload}, format="multipart")

    assert response.status_code == 400
    assert "5 MB" in str(response.json()["cover_image"])


@pytest.mark.parametrize("new_cover", [image_file("new.png"), ""], ids=["replaced", "removed"])
def test_old_cover_file_is_deleted(admin_client, recipe, new_cover, django_capture_on_commit_callbacks):
    recipe.cover_image = image_file("old.png")
    recipe.save()
    old_path = recipe.cover_image.path

    with django_capture_on_commit_callbacks(execute=True):
        response = admin_client.patch(detail_url(recipe), {"cover_image": new_cover}, format="multipart")

    assert response.status_code == 200
    assert not os.path.exists(old_path)


def test_deleting_recipe_deletes_its_files(admin_client, recipe, django_capture_on_commit_callbacks):
    recipe.cover_image = image_file("cover.png")
    recipe.save()
    gallery = RecipeImage.objects.create(recipe=recipe, image=image_file("gallery.png"))
    paths = [recipe.cover_image.path, gallery.image.path]

    with django_capture_on_commit_callbacks(execute=True):
        assert admin_client.delete(detail_url(recipe)).status_code == 204

    assert not any(os.path.exists(p) for p in paths)


def test_ratings_are_shown_per_admin_with_average(user_client, admin, friend):
    both = make_recipe("Both")
    RecipeReview.objects.create(recipe=both, author=admin, rating=8)
    RecipeReview.objects.create(recipe=both, author=friend, rating=5)
    one = make_recipe("One")
    RecipeReview.objects.create(recipe=one, author=admin, rating=9)

    by_title = {r["title"]: r for r in user_client.get(LIST_URL).json()}

    assert by_title["Both"]["ratings"] == {"admin": 8, "friend": 5}
    assert by_title["Both"]["combined_rating"] == 6.5
    # Rated by only one admin: the average of that one rating, not pulled down by the missing one
    assert by_title["One"]["ratings"] == {"admin": 9, "friend": None}
    assert by_title["One"]["combined_rating"] == 9.0


def test_ordering_by_rating_puts_unrated_last(admin_client, admin, friend):
    low = make_recipe("Low")
    RecipeReview.objects.create(recipe=low, author=admin, rating=3)
    high = make_recipe("High")
    RecipeReview.objects.create(recipe=high, author=friend, rating=9)
    make_recipe("Unrated")

    assert titles(admin_client.get(LIST_URL, {"ordering": "-combined_rating"})) == ["High", "Low", "Unrated"]
    assert titles(admin_client.get(LIST_URL, {"ordering": "combined_rating"})) == ["Low", "High", "Unrated"]
    assert titles(admin_client.get(LIST_URL, {"ordering": "-rating:admin"})) == ["Low", "Unrated", "High"]


def test_ordering_by_unknown_admin_is_rejected(admin_client):
    response = admin_client.get(LIST_URL, {"ordering": "rating:nobody"})

    assert response.status_code == 400


def test_search_ranks_title_matches_first(admin_client):
    # The title match is older, so newest-first alone would put it last
    make_recipe("Egg fried rice", instructions="Fry the rice.")
    make_recipe("Pancakes", instructions="Mix flour and an egg.")
    make_recipe("Toast", instructions="Toast the bread.")

    assert titles(admin_client.get(LIST_URL, {"search": "egg"})) == ["Egg fried rice", "Pancakes"]


def test_filter_by_ingredient(admin_client, recipe):
    make_recipe("Without tomato")

    response = admin_client.get(LIST_URL, {"ingredient": recipe.ingredients.get().pk})

    assert titles(response) == ["Salad"]
