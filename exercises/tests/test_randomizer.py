import pytest
from django.urls import reverse

from exercises.models import TrainingPlan
from exercises.tests.helpers import make_exercise


def picked(client, **params):
    response = client.get(reverse("exercise-random"), params)
    assert response.status_code == 200
    return [item["id"] for item in response.json()["exercises"]]


def test_randomizer_is_admin_only(user_client):
    assert user_client.get(reverse("exercise-random")).status_code == 403


def test_returns_count_without_repeats_or_saving(admin_client, db):
    for index in range(6):
        make_exercise(f"Exercise {index}")

    ids = picked(admin_client, count=4)

    assert len(ids) == len(set(ids)) == 4
    assert not TrainingPlan.objects.exists()


def test_default_count_is_five(admin_client, db):
    for index in range(6):
        make_exercise(f"Exercise {index}")

    assert len(picked(admin_client)) == 5


def test_returns_fewer_when_too_few_match(admin_client, exercise):
    assert picked(admin_client, count=5) == [exercise.pk]
    assert picked(admin_client, muscle="LEGS") == []


def test_archived_is_never_picked(admin_client, archived):
    assert picked(admin_client, count=20) == []


def test_muscle_matches_any_listed(admin_client, db):
    chest = make_exercise("Press", muscle_categories=["CHEST"])
    back = make_exercise("Row", muscle_categories=["BACK", "ARMS"])
    make_exercise("Squat", muscle_categories=["LEGS"])

    assert set(picked(admin_client, muscle="CHEST,BACK")) == {chest.pk, back.pk}


def test_load_and_intensity_filters(admin_client, db):
    match = make_exercise("Match", load_category="LIGHT", intensity=3)
    make_exercise("Too easy", load_category="LIGHT", intensity=1)
    make_exercise("Too hard", load_category="MEDIUM", intensity=5)
    make_exercise("Wrong load", load_category="HEAVY", intensity=3)

    ids = picked(admin_client, load="LIGHT,MEDIUM", intensity_min=2, intensity_max=4)

    assert ids == [match.pk]


@pytest.mark.parametrize(
    "params, field",
    [
        ({"count": 0}, "count"),
        ({"count": 21}, "count"),
        ({"muscle": "WINGS"}, "muscle"),
        ({"load": "EXTREME"}, "load"),
        ({"intensity_min": 6}, "intensity_min"),
        ({"intensity_min": 4, "intensity_max": 2}, "non_field_errors"),
    ],
)
def test_invalid_query_gives_400(admin_client, db, params, field):
    response = admin_client.get(reverse("exercise-random"), params)

    assert response.status_code == 400
    assert field in response.json()
