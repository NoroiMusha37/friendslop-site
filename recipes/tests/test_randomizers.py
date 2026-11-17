import random
from collections import Counter
from itertools import combinations

import pytest
from django.urls import reverse

from recipes.models import Ingredient, IngredientPair
from recipes.randomizers import naive, smart

URL = reverse("ingredient-random")
# Pair scores. Average with tomato + basil: mozzarella 1.65, garlic 0.4 (below the 0.5 minimum).
# Chocolate goes only with basil; kale has no pairs (like an ingredient added by hand)
SCORES = {
    ("tomato", "basil"): 2.0,
    ("tomato", "mozzarella"): 1.5,
    ("basil", "mozzarella"): 1.8,
    ("tomato", "garlic"): 0.6,
    ("basil", "garlic"): 0.2,
    ("chocolate", "basil"): 0.6,
}


@pytest.fixture
def ids(db):
    names = ["tomato", "basil", "mozzarella", "garlic", "chocolate", "kale"]
    ids = {name: Ingredient.objects.create(name=name).id for name in names}
    for (a, b), score in SCORES.items():
        first, second = sorted((ids[a], ids[b]))
        IngredientPair.objects.create(ingredient_a_id=first, ingredient_b_id=second, score=score)
    return ids


def names(ids, result):
    by_id = {i: name for name, i in ids.items()}
    return [by_id[i] for i in result]


def test_smart_only_combines_ingredients_that_have_a_pair(ids):
    stored = {frozenset(pair) for pair in SCORES}

    for seed in range(50):
        result = names(ids, smart(5, [], random.Random(seed)))

        assert all(frozenset(pair) in stored for pair in combinations(result, 2))


def test_smart_drops_low_averages_and_stops_when_nothing_fits(ids):
    # garlic averages 0.4 with tomato + basil; after mozzarella nothing pairs with all three
    assert names(ids, smart(5, [ids["tomato"], ids["basil"]], random.Random(0))) == ["tomato", "basil", "mozzarella"]


def test_smart_picks_better_fitting_ingredients_more_often(ids):
    rng = random.Random(0)

    picks = Counter(names(ids, smart(2, [ids["tomato"]], rng))[1] for _ in range(3000))

    # Weighted by score with tomato: basil 2.0, mozzarella 1.5, garlic 0.6 out of 4.1
    for name, score in [("basil", 2.0), ("mozzarella", 1.5), ("garlic", 0.6)]:
        assert picks[name] / 3000 == pytest.approx(score / 4.1, abs=0.03)


def test_included_ingredient_without_pairs_doesnt_block(ids):
    result = names(ids, smart(3, [ids["kale"], ids["tomato"]], random.Random(0)))

    assert result[:2] == ["kale", "tomato"]
    assert result[2] in {"basil", "mozzarella", "garlic"}


def test_smart_starts_from_an_ingredient_with_pairs_when_no_included_one_has_any(ids):
    for seed in range(10):
        result = names(ids, smart(3, [ids["kale"]], random.Random(seed)))

        assert result[0] == "kale"
        assert len(result) >= 2 and "kale" not in result[1:]


def test_naive_keeps_included_and_adds_other_random_ingredients(ids):
    result = naive(4, [ids["kale"]], random.Random(0))

    assert result[0] == ids["kale"]
    assert len(set(result)) == 4


def test_endpoint_returns_named_ingredients_in_order(admin_client, ids):
    # tomato given twice counts once
    params = {"mode": "smart", "size": 3, "include": f"{ids['tomato']},{ids['tomato']},{ids['basil']}"}

    response = admin_client.get(URL, params)

    assert response.status_code == 200
    assert [i["name"] for i in response.json()["ingredients"]] == ["tomato", "basil", "mozzarella"]


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({}, "mode"),
        ({"mode": "fancy"}, "mode"),
        ({"mode": "smart", "size": 21}, "size"),
        ({"mode": "smart", "size": 2, "include": "{tomato},{basil},{garlic}"}, "include"),  # more than size
        ({"mode": "naive", "include": "999999"}, "include"),  # unknown id
    ],
)
def test_invalid_parameters_give_400_on_the_field(admin_client, ids, params, field):
    # Real ids are filled in here, so "more than size" isn't caught as "unknown id" instead
    params = {key: value.format(**ids) if isinstance(value, str) else value for key, value in params.items()}

    response = admin_client.get(URL, params)

    assert response.status_code == 400
    assert field in response.json()


def test_user_cannot_use_randomizer(user_client, ids):
    assert user_client.get(URL, {"mode": "naive"}).status_code == 403
