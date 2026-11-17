"""Food randomizer: NAIVE picks random ingredients, SMART builds a combination from ingredient pair scores.

Both take the ingredients to include (kept first, in the given order) and a `random.Random`, so tests can seed it.
"""

import random
from statistics import mean

from django.db.models import Exists, OuterRef, Q

from recipes.models import Ingredient, IngredientPair

MIN_AVERAGE_SCORE = 0.5  # SMART ignores candidates whose average score with the chosen ingredients is lower


def naive(size: int, include: list[int], rng: random.Random) -> list[int]:
    others = list(Ingredient.objects.exclude(id__in=include).order_by("id").values_list("id", flat=True))
    return include + rng.sample(others, min(size - len(include), len(others)))


def partners(ingredient_id: int) -> dict[int, float]:
    """Every ingredient paired with this one -> the pair's score."""
    rows = IngredientPair.objects.filter(Q(ingredient_a=ingredient_id) | Q(ingredient_b=ingredient_id)).values_list(
        "ingredient_a", "ingredient_b", "score"
    )
    return {b if a == ingredient_id else a: score for a, b, score in rows}


def smart(size: int, include: list[int], rng: random.Random) -> list[int]:
    """Adds ingredients paired with every chosen ingredient that has pairs, picked at random weighted by their average
    score with them; stops early when none fits. Included ingredients without pairs (e.g. added by hand) don't block."""
    chosen = list(include)
    scores = {i: partners(i) for i in chosen}
    with_pairs = [i for i in chosen if scores[i]]
    if not with_pairs and len(chosen) < size:
        # Nothing to build on: start from a random ingredient that has pairs
        has_pairs = Exists(
            IngredientPair.objects.filter(Q(ingredient_a=OuterRef("pk")) | Q(ingredient_b=OuterRef("pk")))
        )
        starts = list(Ingredient.objects.filter(has_pairs).order_by("id").values_list("id", flat=True))
        if not starts:
            return chosen
        start = rng.choice(starts)
        chosen.append(start)
        scores[start] = partners(start)
        with_pairs.append(start)

    while len(chosen) < size:
        candidates = set.intersection(*(set(scores[i]) for i in with_pairs)) - set(chosen)
        averages = {c: mean(scores[i][c] for i in with_pairs) for c in candidates}
        fitting = sorted((c, average) for c, average in averages.items() if average >= MIN_AVERAGE_SCORE)
        if not fitting:
            break
        pick = rng.choices([c for c, _ in fitting], weights=[average for _, average in fitting])[0]
        chosen.append(pick)
        scores[pick] = partners(pick)
        with_pairs.append(pick)
    return chosen
