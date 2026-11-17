"""Import of RecipeNLG: ingredients and how well each pair goes together (PMI = ln(together / expected by chance)).

Names come from `recipenlg_names.csv`, reviewed by hand: name -> ingredient, empty = junk. Names not in it are skipped.

The other option is parsing the raw `ingredients` lines with a recipe parser
(e.g. `ingredient-parser-nlp`): cleaner names than `NER`, but hours of parsing.
"""

import csv
import json
import math
from collections import Counter
from collections.abc import Iterator
from itertools import combinations
from pathlib import Path

from django.db import transaction

from recipes.models import Ingredient, IngredientPair, clean_ingredient_name

NAMES_FILE = Path(__file__).with_name("recipenlg_names.csv")
MIN_PAIR_RECIPES = 10  # a pair must appear together this often; fewer gives scores driven by luck
BATCH_SIZE = 5000


def load_names() -> dict[str, str]:
    """`NER` name -> ingredient, without the junk names."""
    with NAMES_FILE.open(encoding="utf-8", newline="") as f:
        return {row["name"]: row["ingredient"] for row in csv.DictReader(f) if row["ingredient"]}


def read_recipes(path: Path) -> Iterator[set[str]]:
    """Each recipe's ingredient names (the `NER` column), with the basic cleanup of hand-typed names."""
    csv.field_size_limit(10**8)  # a few recipes have very long fields
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            yield {clean_ingredient_name(name) for name in json.loads(row["NER"]) if name.strip()}


def count(path: Path, names: dict[str, str]) -> tuple[int, Counter, Counter]:
    """How many recipes there are, and how many contain each ingredient and each pair of ingredients."""
    recipes, single, pairs = 0, Counter(), Counter()
    for recipe in read_recipes(path):
        recipes += 1
        ingredients = sorted({names[name] for name in recipe if name in names})
        single.update(ingredients)
        pairs.update(combinations(ingredients, 2))
    return recipes, single, pairs


def scores(recipes: int, single: Counter, pairs: Counter) -> Iterator[tuple[str, str, float]]:
    """Pairs seen together often enough, with their PMI; pairs below chance (PMI < 0) are left out."""
    for (a, b), together in pairs.items():
        if together >= MIN_PAIR_RECIPES:
            score = math.log(together * recipes / (single[a] * single[b]))
            if score >= 0:
                yield a, b, score


def save(ingredients: set[str], scored: Iterator[tuple[str, str, float]]) -> int:
    """Adds missing ingredients (existing ones keep their ids) and replaces all pairs, in one transaction."""
    with transaction.atomic():
        Ingredient.objects.bulk_create(
            [Ingredient(name=name) for name in ingredients],
            ignore_conflicts=True,
            batch_size=BATCH_SIZE,
        )
        ids = dict(Ingredient.objects.filter(name__in=ingredients).values_list("name", "id"))
        IngredientPair.objects.all().delete()
        # Each pair is stored with the smaller id first; existing ingredients keep older ids, so names don't tell
        new_pairs = [
            IngredientPair(ingredient_a_id=min(ids[a], ids[b]), ingredient_b_id=max(ids[a], ids[b]), score=score)
            for a, b, score in scored
        ]
        IngredientPair.objects.bulk_create(new_pairs, batch_size=BATCH_SIZE)
    return len(new_pairs)


def import_recipenlg(path: Path) -> dict:
    """Reads the CSV once, then saves; returns a summary for the command's output."""
    names = load_names()
    recipes, single, pairs = count(path, names)
    stored = save(set(names.values()), scores(recipes, single, pairs))
    return {"recipes": recipes, "ingredients": len(set(names.values())), "pairs": stored}
