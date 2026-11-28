import pytest
from django.urls import reverse

from exercises.models import Exercise, ExerciseReview
from exercises.tests.helpers import make_exercise

BODY = {
    "name": "Squat",
    "description": "Sit and stand.",
    "muscle_categories": ["LEGS", "CORE"],
    "load_category": "HEAVY",
    "intensity": 4,
}


def detail(exercise):
    return reverse("exercise-detail", args=[exercise.pk])


def test_admin_creates_exercise(admin_client):
    response = admin_client.post(reverse("exercise-list"), BODY, format="json")

    assert response.status_code == 201
    assert response.json()["muscle_categories"] == ["LEGS", "CORE"]
    assert response.json()["links"] == []


def test_regular_user_reads_but_cant_write(user_client, exercise):
    assert user_client.get(detail(exercise)).status_code == 200
    assert user_client.post(reverse("exercise-list"), BODY, format="json").status_code == 403
    assert user_client.patch(detail(exercise), {"name": "X"}, format="json").status_code == 403
    assert user_client.post(reverse("exercise-archive", args=[exercise.pk])).status_code == 403


@pytest.mark.parametrize(
    "field, value",
    [
        ("muscle_categories", []),
        ("muscle_categories", ["WINGS"]),
        ("load_category", "EXTREME"),
        ("intensity", 0),
        ("intensity", 6),
    ],
)
def test_invalid_fields_are_rejected(admin_client, field, value):
    response = admin_client.post(reverse("exercise-list"), {**BODY, field: value}, format="json")

    assert response.status_code == 400
    assert field in response.json()


def test_name_is_unique_ignoring_case_even_against_archived(admin_client, archived):
    response = admin_client.post(reverse("exercise-list"), {**BODY, "name": "OLD CURL"}, format="json")

    assert response.status_code == 400
    assert "name" in response.json()


def test_exercise_keeps_its_own_name_on_edit(admin_client, exercise):
    response = admin_client.patch(detail(exercise), {"name": exercise.name, "intensity": 5}, format="json")

    assert response.status_code == 200
    assert response.json()["intensity"] == 5


def test_exercise_cant_be_deleted_or_replaced(admin_client, exercise):
    assert admin_client.delete(detail(exercise)).status_code == 405
    assert admin_client.put(detail(exercise), BODY, format="json").status_code == 405


def test_list_hides_archived_by_default(admin_client, exercise, archived):
    response = admin_client.get(reverse("exercise-list"))

    assert [item["id"] for item in response.json()] == [exercise.pk]


def test_admin_lists_archived_on_request(admin_client, exercise, archived):
    response = admin_client.get(reverse("exercise-list"), {"archived": "true"})

    assert [item["id"] for item in response.json()] == [archived.pk]


def test_regular_user_cant_list_archived_but_can_open_one(user_client, archived):
    assert user_client.get(reverse("exercise-list"), {"archived": "true"}).status_code == 403
    assert user_client.get(detail(archived)).status_code == 200


def test_list_filters(admin_client, exercise):
    match = make_exercise("Row", muscle_categories=["BACK", "ARMS"], load_category="HEAVY", intensity=4)

    response = admin_client.get(
        reverse("exercise-list"),
        {"muscle": "ARMS", "load": "HEAVY", "intensity": 4, "search": "ro"},
    )

    assert [item["id"] for item in response.json()] == [match.pk]


def test_archive_and_restore(admin_client, exercise):
    archive = reverse("exercise-archive", args=[exercise.pk])
    restore = reverse("exercise-restore", args=[exercise.pk])

    assert admin_client.post(restore).status_code == 409
    assert admin_client.post(archive).json()["archived_at"] is not None
    assert admin_client.post(archive).status_code == 409
    assert admin_client.post(restore).json()["archived_at"] is None


def test_archived_exercise_cant_be_changed(admin_client, archived):
    response = admin_client.patch(detail(archived), {"intensity": 5}, format="json")

    assert response.status_code == 409
    assert Exercise.objects.get(pk=archived.pk).intensity == 2


def test_archived_exercise_reviews_are_read_only(admin_client, admin, archived):
    url = reverse("exercise-review", args=[archived.pk])
    assert admin_client.post(url, {"rating": 5}, format="json").status_code == 409

    ExerciseReview.objects.create(exercise=archived, author=admin, rating=3)

    assert admin_client.patch(url, {"rating": 9}, format="json").status_code == 409
    assert admin_client.delete(url).status_code == 409
    assert ExerciseReview.objects.get(exercise=archived).rating == 3


def test_active_exercise_can_be_reviewed(admin_client, exercise):
    response = admin_client.post(reverse("exercise-review", args=[exercise.pk]), {"rating": 7}, format="json")

    assert response.status_code == 201
    assert admin_client.get(detail(exercise)).json()["combined_rating"] == 7
