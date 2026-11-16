from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from conftest import PASSWORD
from recipes.models import Recipe, RecipeComment


def comments_url(recipe):
    return reverse("recipe-comments", args=[recipe.pk])


def comment_url(comment):
    return reverse("recipe-delete-comment", args=[comment.recipe_id, comment.pk])


@pytest.fixture
def comment(user, recipe):
    return RecipeComment.objects.create(recipe=recipe, author=user, text="Tasty")


def test_comments_are_listed_newest_first(user_client, user, recipe):
    # Saved out of time order, so neither insertion order nor its reverse matches the expected one
    now = timezone.now()
    for text, minutes_ago in [("Middle", 5), ("Old", 10), ("New", 0)]:
        comment = RecipeComment.objects.create(recipe=recipe, author=user, text=text)
        RecipeComment.objects.filter(pk=comment.pk).update(
            created_at=now - timedelta(minutes=minutes_ago),
        )

    response = user_client.get(comments_url(recipe))

    assert [c["text"] for c in response.json()] == ["New", "Middle", "Old"]


def test_user_posts_comment(user_client, recipe):
    response = user_client.post(comments_url(recipe), {"text": "Tasty"}, format="json")

    assert response.status_code == 201
    assert response.json()["author"] == "user"
    assert recipe.comments.get().text == "Tasty"


def test_admin_cannot_post_comment(admin_client, recipe):
    response = admin_client.post(comments_url(recipe), {"text": "Tasty"}, format="json")

    assert response.status_code == 403
    assert not recipe.comments.exists()


def test_too_long_comment_is_refused(user_client, recipe):
    response = user_client.post(comments_url(recipe), {"text": "a" * 2001}, format="json")

    assert response.status_code == 400
    assert not recipe.comments.exists()


@pytest.mark.parametrize("client_fixture", ["user_client", "admin_client"])
def test_author_or_admin_deletes_comment(request, client_fixture, comment):
    client = request.getfixturevalue(client_fixture)

    assert client.delete(comment_url(comment)).status_code == 204
    assert not RecipeComment.objects.exists()


def test_other_user_cannot_delete_comment(api_client, comment):
    other = User.objects.create_user(
        "other",
        "other@example.com",
        PASSWORD,
        approved_at=timezone.now(),
    )
    api_client.force_authenticate(other)

    assert api_client.delete(comment_url(comment)).status_code == 403
    assert RecipeComment.objects.exists()


def test_comment_is_deleted_only_through_its_recipe(admin_client, comment):
    other_recipe = Recipe.objects.create(title="Soup", instructions="Boil.", cooking_method="BOILED")
    url = reverse("recipe-delete-comment", args=[other_recipe.pk, comment.pk])

    assert admin_client.delete(url).status_code == 404
    assert RecipeComment.objects.exists()
