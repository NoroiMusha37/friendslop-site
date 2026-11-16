import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from recipes.filters import MAX_SEARCH_RESULTS
from recipes.models import Ingredient

LIST_URL = reverse("ingredient-list")


def names(response):
    return [ingredient["name"] for ingredient in response.json()]


def test_search_puts_names_starting_with_text_first_then_shorter(user_client):
    # Saved out of the expected order, so neither id nor insertion order can pass the test
    for name in ["olive oil", "boiled egg", "palm oil", "oil spray", "tomato", "corn oil", "oil"]:
        Ingredient.objects.create(name=name)

    response = user_client.get(LIST_URL, {"search": " OIL "})

    assert names(response) == ["oil", "oil spray", "corn oil", "palm oil", "olive oil", "boiled egg"]


def test_search_returns_at_most_20(user_client):
    Ingredient.objects.bulk_create(Ingredient(name=f"salt {i}") for i in range(MAX_SEARCH_RESULTS + 1))

    assert len(user_client.get(LIST_URL, {"search": "salt"}).json()) == MAX_SEARCH_RESULTS


@pytest.mark.parametrize("params", [{"search": " t "}, {}])
def test_short_or_missing_search_gives_nothing(user_client, ingredient, params):
    assert user_client.get(LIST_URL, params).json() == []


def test_admin_adds_ingredient_with_cleaned_name(admin_client):
    response = admin_client.post(LIST_URL, {"name": "  Sweet   Potato "}, format="json")

    assert response.status_code == 201
    assert Ingredient.objects.get().name == "sweet potato"


def test_existing_name_is_refused_after_cleanup(admin_client, ingredient):
    response = admin_client.post(LIST_URL, {"name": "Tomato "}, format="json")

    assert response.status_code == 400
    assert response.json() == {"name": ["This ingredient already exists."]}


def test_user_cannot_add_ingredient(user_client):
    response = user_client.post(LIST_URL, {"name": "salt"}, format="json")

    assert response.status_code == 403
    assert not Ingredient.objects.exists()


def test_admin_deletes_unused_ingredient(admin_client, ingredient):
    response = admin_client.delete(reverse("ingredient-detail", args=[ingredient.pk]))

    assert response.status_code == 204
    assert not Ingredient.objects.exists()


def test_used_ingredient_is_not_deleted(admin_client, recipe, ingredient):
    response = admin_client.delete(reverse("ingredient-detail", args=[ingredient.pk]))

    assert response.status_code == 409
    assert response.json() == {"detail": "This ingredient is used in 1 recipe(s)."}
    assert Ingredient.objects.exists()


def test_admin_panel_cleanup_catches_duplicate(ingredient):
    # Django admin forms validate through full_clean(), which runs the model's clean() before the unique check
    with pytest.raises(ValidationError, match="already exists"):
        Ingredient(name=" Tomato ").full_clean()
