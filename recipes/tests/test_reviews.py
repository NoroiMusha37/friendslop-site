import pytest
from django.urls import reverse

from common.models import REVIEW_TEXT_MAX_LENGTH
from recipes.models import RecipeReview


def review_url(recipe):
    return reverse("recipe-review", args=[recipe.pk])


def test_admin_creates_own_review(admin_client, recipe):
    response = admin_client.post(review_url(recipe), {"rating": 8}, format="json")

    assert response.status_code == 201
    assert response.json() == {
        "id": recipe.reviews.get().id,
        "author": "admin",
        "rating": 8,
        "text": "",
    }


def test_second_review_by_same_admin_is_refused(admin_client, admin, recipe):
    RecipeReview.objects.create(recipe=recipe, author=admin, rating=5)

    response = admin_client.post(review_url(recipe), {"rating": 8}, format="json")

    assert response.status_code == 409
    assert recipe.reviews.get().rating == 5


def test_patch_changes_only_given_fields(admin_client, admin, recipe):
    RecipeReview.objects.create(recipe=recipe, author=admin, rating=5, text="Fine")

    response = admin_client.patch(review_url(recipe), {"text": "Great"}, format="json")

    assert response.status_code == 200
    assert (response.json()["rating"], response.json()["text"]) == (5, "Great")


def test_admin_deletes_only_own_review(admin_client, admin, friend, recipe):
    RecipeReview.objects.create(recipe=recipe, author=admin, rating=5)
    RecipeReview.objects.create(recipe=recipe, author=friend, rating=7)

    assert admin_client.delete(review_url(recipe)).status_code == 204
    assert list(recipe.reviews.values_list("author__username", flat=True)) == ["friend"]


def test_other_admins_review_is_not_reachable(admin_client, friend, recipe):
    RecipeReview.objects.create(recipe=recipe, author=friend, rating=7)

    patched = admin_client.patch(review_url(recipe), {"rating": 1}, format="json")

    assert patched.status_code == 404
    assert admin_client.delete(review_url(recipe)).status_code == 404
    assert recipe.reviews.get().rating == 7


def test_user_cannot_review(user_client, recipe):
    response = user_client.post(review_url(recipe), {"rating": 8}, format="json")

    assert response.status_code == 403


@pytest.mark.parametrize(
    "data",
    [
        {"rating": 11},
        {"rating": 8, "text": "a" * (REVIEW_TEXT_MAX_LENGTH + 1)},
    ],
)
def test_invalid_review_is_refused(admin_client, recipe, data):
    assert admin_client.post(review_url(recipe), data, format="json").status_code == 400
    assert not recipe.reviews.exists()


def test_detail_lists_reviews_in_admin_order(user_client, admin, friend, recipe):
    # Friend's review is created first, so the default id order would put it first
    RecipeReview.objects.create(recipe=recipe, author=friend, rating=7)
    RecipeReview.objects.create(recipe=recipe, author=admin, rating=5)

    response = user_client.get(reverse("recipe-detail", args=[recipe.pk]))

    assert [review["author"] for review in response.json()["reviews"]] == ["admin", "friend"]
