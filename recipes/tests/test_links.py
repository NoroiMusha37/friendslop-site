from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from responses import matchers

from common.youtube import API_URL
from conftest import youtube_video
from recipes.models import Recipe, RecipeLink

VIDEO = "dQw4w9WgXcQ"
GONE_VIDEO = "9bZkp7q19f0"


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


def add_links_without_info(recipe, *urls):
    return [RecipeLink.objects.create(recipe=recipe, url=url) for url in urls]


def test_refresh_fills_only_this_recipes_missing_youtube_info(admin_client, recipe, youtube):
    _, gone, _ = add_links_without_info(
        recipe,
        f"https://youtu.be/{VIDEO}",
        f"https://youtu.be/{GONE_VIDEO}",
        "https://a.com",
    )
    RecipeLink.objects.create(recipe=recipe, url="https://youtu.be/AAAAAAAAAAA", title="Has info")
    other = Recipe.objects.create(title="Soup", instructions="Boil.", cooking_method="BOILED")
    add_links_without_info(other, "https://youtu.be/BBBBBBBBBBB")
    # Only the links without info of this recipe are asked for; the gone video isn't in the reply
    youtube.get(
        API_URL,
        json={"items": [youtube_video(VIDEO, title="How to chop")]},
        match=[matchers.query_param_matcher({"id": f"{VIDEO},{GONE_VIDEO}"}, strict_match=False)],
    )

    response = admin_client.post(reverse("recipe-refresh-links", args=[recipe.pk]))

    assert response.status_code == 200
    assert [link["title"] for link in response.json()["links"]] == ["How to chop", "", "", "Has info"]
    assert response.json()["not_found"] == [gone.id]
    assert RecipeLink.objects.get(recipe=recipe, url=f"https://youtu.be/{VIDEO}").title == "How to chop"


def test_global_refresh_fills_every_recipes_links(admin_client, recipe, youtube):
    other = Recipe.objects.create(title="Soup", instructions="Boil.", cooking_method="BOILED")
    add_links_without_info(recipe, f"https://youtu.be/{VIDEO}")
    add_links_without_info(other, f"https://youtu.be/{GONE_VIDEO}")
    youtube.get(API_URL, json={"items": [youtube_video(VIDEO)]})

    response = admin_client.post(reverse("refresh-links"))

    assert response.json() == {
        "filled": 1,
        "not_found": [{"url": f"https://youtu.be/{GONE_VIDEO}", "type": "recipe", "object_id": other.pk}],
    }
    assert RecipeLink.objects.filter(title="Video").count() == 1


def test_refresh_while_youtube_is_down_gives_503(admin_client, recipe, youtube):
    add_links_without_info(recipe, f"https://youtu.be/{VIDEO}")
    youtube.get(API_URL, status=500)

    response = admin_client.post(reverse("refresh-links"))

    assert response.status_code == 503
    assert not RecipeLink.objects.exclude(title="").exists()


def test_refresh_queries_dont_grow_with_links(admin_client, youtube):
    videos = [f"video{i:06d}" for i in range(5)]
    youtube.get(API_URL, json={"items": [youtube_video(video) for video in videos]})
    one_link = Recipe.objects.create(title="One", instructions="I", cooking_method="RAW")
    many_links = Recipe.objects.create(title="Many", instructions="I", cooking_method="RAW")
    RecipeLink.objects.create(recipe=one_link, url=f"https://youtu.be/{videos[0]}")
    for video in videos[1:]:
        RecipeLink.objects.create(recipe=many_links, url=f"https://youtu.be/{video}")

    def queries(recipe):
        with CaptureQueriesContext(connection) as captured:
            response = admin_client.post(reverse("recipe-refresh-links", args=[recipe.pk]))
        assert response.status_code == 200
        return len(captured)

    assert queries(many_links) == queries(one_link)


def test_user_cannot_refresh_links(user_client):
    assert user_client.post(reverse("refresh-links")).status_code == 403
