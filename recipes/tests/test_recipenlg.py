import csv
import json
import math

import pytest

from recipes.models import Ingredient, IngredientPair, clean_ingredient_name
from recipes.recipenlg import NAMES_FILE, import_recipenlg

# 7 recipes. Through the names file (`tomatoes` -> tomato, `fresh basil` -> basil; `Tomato ` is cleaned to tomato),
# each ingredient's recipes: tomato 4, basil 3, salt 3, sugar 3, flour 2, water 6. `#` and `pans` are junk in the file,
# `saffron` isn't in it
RECIPES = [
    ["tomatoes", "fresh basil"],
    ["tomato", "basil", "salt", "water"],
    ["tomato", "basil", "water"],
    ["salt", "sugar", "water", "#", "pans"],
    ["sugar", "flour", "water"],
    ["salt", "flour", "saffron", "water", "Tomato "],
    ["#", "sugar", "pans", "water"],
]
NAMES = {
    "tomato": "tomato",
    "tomatoes": "tomato",
    "basil": "basil",
    "fresh basil": "basil",
    "salt": "salt",
    "sugar": "sugar",
    "flour": "flour",
    "water": "water",
    "#": "",
    "pans": "",
}


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return path


@pytest.fixture
def small_import(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "recipes.recipenlg.NAMES_FILE", write_csv(tmp_path / "names.csv", ["name", "ingredient"], NAMES.items())
    )
    monkeypatch.setattr("recipes.recipenlg.MIN_PAIR_RECIPES", 2)
    rows = ([f"Recipe {i}", json.dumps(names)] for i, names in enumerate(RECIPES))
    return write_csv(tmp_path / "recipes.csv", ["title", "NER"], rows)


def stored_pairs():
    return {
        frozenset((pair.ingredient_a.name, pair.ingredient_b.name)): pair.score
        for pair in IngredientPair.objects.select_related("ingredient_a", "ingredient_b")
    }


def test_names_file_is_consistent():
    with NAMES_FILE.open(encoding="utf-8", newline="") as f:
        names = {row["name"]: row["ingredient"] for row in csv.DictReader(f)}

    # Recipe names are matched after the basic cleanup, so a name written any other way would never match
    assert [name for name in names if clean_ingredient_name(name) != name] == []
    # An ingredient that is also a listed name must map to itself, otherwise two ingredients mean the same thing
    assert {i: names[i] for i in names.values() if i in names and names[i] != i} == {}


def test_import_maps_names_and_stores_only_common_fitting_pairs(db, small_import):
    result = import_recipenlg(small_import)

    assert set(Ingredient.objects.values_list("name", flat=True)) == {
        "tomato",
        "basil",
        "salt",
        "sugar",
        "flour",
        "water",
    }
    # tomato+basil: 3 together, 4 * 3 / 7 expected. water+tomato (3 together, 6 * 4 / 7 expected) is below chance,
    # salt+sugar is seen together only once: neither is stored
    assert stored_pairs() == pytest.approx(
        {
            frozenset(("tomato", "basil")): math.log(3 * 7 / (4 * 3)),
            frozenset(("tomato", "salt")): math.log(2 * 7 / (4 * 3)),
            frozenset(("water", "salt")): math.log(3 * 7 / (6 * 3)),
            frozenset(("water", "sugar")): math.log(3 * 7 / (6 * 3)),
            frozenset(("water", "flour")): math.log(2 * 7 / (6 * 2)),
        }
    )
    assert result == {"recipes": 7, "ingredients": 6, "pairs": 5}


def test_reimport_keeps_existing_ingredients_and_replaces_pairs(db, small_import):
    # `water` sorts last but gets the smallest id, so its pairs must be stored with water first
    water = Ingredient.objects.create(name="water")
    kale = Ingredient.objects.create(name="kale")
    leek = Ingredient.objects.create(name="leek")
    IngredientPair.objects.create(ingredient_a=kale, ingredient_b=leek, score=1.0)

    import_recipenlg(small_import)

    assert Ingredient.objects.get(name="water").pk == water.pk
    assert Ingredient.objects.filter(name="kale").exists()
    pairs = stored_pairs()
    assert frozenset(("water", "salt")) in pairs
    assert frozenset(("kale", "leek")) not in pairs
