from django.urls import reverse

from common.youtube import API_URL
from conftest import youtube_video
from recipes.models import Recipe, RecipeLink

VIDEO = "dQw4w9WgXcQ"


def links_url(recipe):
    return reverse("recipe-add-links", args=[recipe.pk])


def test_admin_adds_several_links(admin_client, recipe, youtube):
    youtube.get(API_URL, json={"items": [youtube_video(VIDEO, title="How to chop")]})

    response = admin_client.post(
        links_url(recipe),
        {"links": [f"https://youtu.be/{VIDEO}", "https://a.com"]},
        format="json",
    )

    assert response.status_code == 201
    assert [link["title"] for link in response.json()] == ["How to chop", ""]
    assert recipe.links.count() == 2


def test_one_bad_link_saves_none(admin_client, recipe, youtube):
    youtube.get(API_URL, json={"items": []})

    response = admin_client.post(
        links_url(recipe),
        {"links": ["https://a.com", f"https://youtu.be/{VIDEO}"]},
        format="json",
    )

    assert response.status_code == 400
    assert response.json() == {"links": {"1": ["YouTube video not found."]}}
    assert not recipe.links.exists()


def test_invalid_api_key_gives_503(admin_client, recipe, youtube):
    youtube.get(
        API_URL,
        status=400,
        json={"error": {"errors": [{"reason": "badRequest"}]}},
    )

    response = admin_client.post(
        links_url(recipe),
        {"links": [f"https://youtu.be/{VIDEO}"]},
        format="json",
    )

    assert response.status_code == 503
    assert not recipe.links.exists()


def test_recipe_is_created_with_links(admin_client, ingredient, youtube):
    data = {
        "title": "Soup",
        "instructions": "Boil.",
        "cooking_method": "BOILED",
        "ingredients": [ingredient.pk],
    }

    response = admin_client.post(
        reverse("recipe-list"),
        {**data, "links": ["https://a.com"]},
        format="json",
    )

    assert response.status_code == 201
    assert [link["url"] for link in response.json()["links"]] == ["https://a.com"]


def test_recipe_with_broken_link_is_not_created(admin_client, ingredient, youtube):
    youtube.get(API_URL, json={"items": []})
    data = {
        "title": "Soup",
        "instructions": "Boil.",
        "cooking_method": "BOILED",
        "ingredients": [ingredient.pk],
    }

    response = admin_client.post(
        reverse("recipe-list"),
        {**data, "links": [f"https://youtu.be/{VIDEO}"]},
        format="json",
    )

    assert response.status_code == 400
    assert not Recipe.objects.exists()


def test_admin_deletes_link_of_that_recipe_only(admin_client, recipe):
    link = RecipeLink.objects.create(recipe=recipe, url="https://a.com")
    other = Recipe.objects.create(
        title="Other",
        instructions="-",
        cooking_method="RAW",
    )

    assert admin_client.delete(reverse("recipe-delete-link", args=[other.pk, link.pk])).status_code == 404
    assert admin_client.delete(reverse("recipe-delete-link", args=[recipe.pk, link.pk])).status_code == 204
    assert not RecipeLink.objects.exists()


def test_regular_user_cant_change_links(user_client, recipe):
    link = RecipeLink.objects.create(recipe=recipe, url="https://a.com")

    assert (
        user_client.post(
            links_url(recipe),
            {"links": ["https://b.com"]},
            format="json",
        ).status_code
        == 403
    )
    assert user_client.delete(reverse("recipe-delete-link", args=[recipe.pk, link.pk])).status_code == 403
