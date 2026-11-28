import pytest
from django.urls import reverse

from exercises.models import PlanMode, TrainingPlan, UserFavouritePlan
from exercises.tests.helpers import make_exercise, make_plan


def save(client, exercises, mode="MANUAL", **fields):
    return client.post(
        reverse("plan-list"),
        {
            "name": "Leg day",
            "mode": mode,
            "exercises": [exercise.pk for exercise in exercises],
            **fields,
        },
        format="json",
    )


def favourite_url(plan):
    return reverse("plan-favourite", args=[plan.pk])


def test_admin_saves_plan_in_given_order_with_repeats(admin_client, admin, exercise):
    other = make_exercise("Row")

    response = save(admin_client, [other, exercise, other])

    assert response.status_code == 201
    assert [item["id"] for item in response.json()["exercises"]] == [other.pk, exercise.pk, other.pk]
    assert response.json()["user"] == admin.username
    assert response.json()["source_plan"] is None


def test_regular_user_reads_plans_but_cant_write(user_client, exercise):
    plan = make_plan(exercise)

    assert user_client.get(reverse("plan-detail", args=[plan.pk])).status_code == 200
    assert save(user_client, [exercise]).status_code == 403
    assert user_client.put(favourite_url(plan)).status_code == 403


def test_plan_needs_a_name_and_exercises(admin_client, exercise):
    assert "exercises" in save(admin_client, []).json()
    assert "name" in save(admin_client, [exercise], name="").json()


def test_unknown_exercise_is_rejected(admin_client):
    response = admin_client.post(
        reverse("plan-list"),
        {"name": "X", "mode": "MANUAL", "exercises": [999]},
        format="json",
    )

    assert response.status_code == 400
    assert "exercises" in response.json()


def test_plan_has_no_edit_or_delete(admin_client, exercise):
    url = reverse("plan-detail", args=[make_plan(exercise).pk])

    assert admin_client.patch(url, {"name": "X"}, format="json").status_code == 405
    assert admin_client.put(url, {"name": "X"}, format="json").status_code == 405
    assert admin_client.delete(url).status_code == 405


def test_editing_creates_a_copy_and_leaves_the_source(admin_client, exercise):
    other = make_exercise("Row")
    source = make_plan(exercise, other)

    response = save(admin_client, [other, exercise], source_plan=source.pk)

    assert response.status_code == 201
    assert response.json()["source_plan"] == source.pk
    assert list(source.items.values_list("exercise_id", flat=True)) == [exercise.pk, other.pk]


@pytest.mark.parametrize(
    "source_mode, sent, status_code",
    [
        (PlanMode.RANDOM, "RANDOM_EDIT", 201),
        (PlanMode.RANDOM, "RANDOM", 400),
        (PlanMode.RANDOM_EDIT, "RANDOM_EDIT", 201),
        (PlanMode.RANDOM_EDIT, "MANUAL", 400),
        (PlanMode.MANUAL, "MANUAL", 201),
        (PlanMode.MANUAL, "RANDOM_EDIT", 400),
    ],
)
def test_copy_mode_follows_the_source(admin_client, exercise, source_mode, sent, status_code):
    source = make_plan(exercise, mode=source_mode)

    assert save(admin_client, [exercise], mode=sent, source_plan=source.pk).status_code == status_code


def test_archived_exercise_cant_be_added_to_a_plan(admin_client, archived):
    assert save(admin_client, [archived]).status_code == 409


def test_plan_with_archived_exercise_cant_be_edited_even_by_dropping_it(admin_client, exercise, archived):
    source = make_plan(exercise, archived)

    assert save(admin_client, [exercise], source_plan=source.pk).status_code == 409


def test_plan_shows_its_archived_exercise(admin_client, archived):
    plan = make_plan(archived)

    response = admin_client.get(reverse("plan-detail", args=[plan.pk]))

    assert response.json()["exercises"][0]["is_archived"] is True


def test_list_shows_latest_versions_and_history_on_request(admin_client, exercise):
    source = make_plan(exercise)
    copy = make_plan(exercise, source_plan=source)

    latest = admin_client.get(reverse("plan-list")).json()
    history = admin_client.get(reverse("plan-list"), {"history": "true"}).json()

    assert [plan["id"] for plan in latest] == [copy.pk]
    assert [plan["id"] for plan in history] == [copy.pk, source.pk]


def test_favourites_are_personal_and_idempotent(admin_client, admin, friend, exercise):
    plan = make_plan(exercise)
    UserFavouritePlan.objects.create(user=friend, plan=plan)
    url = reverse("plan-detail", args=[plan.pk])

    assert admin_client.get(url).json()["is_favourite"] is False
    assert admin_client.put(favourite_url(plan)).status_code == 204
    assert admin_client.put(favourite_url(plan)).status_code == 204
    assert admin_client.get(url).json()["is_favourite"] is True

    assert admin_client.delete(favourite_url(plan)).status_code == 204
    assert admin_client.delete(favourite_url(plan)).status_code == 204
    assert UserFavouritePlan.objects.filter(plan=plan).get().user == friend


def test_favourite_doesnt_create_a_plan_and_works_with_archived(admin_client, archived):
    plan = make_plan(archived)

    assert admin_client.put(favourite_url(plan)).status_code == 204
    assert TrainingPlan.objects.count() == 1


def test_copy_doesnt_inherit_favourites(admin_client, admin, exercise):
    source = make_plan(exercise)
    UserFavouritePlan.objects.create(user=admin, plan=source)

    response = save(admin_client, [exercise], source_plan=source.pk)

    assert response.json()["is_favourite"] is False


def test_favourite_filter_finds_an_edited_plan(admin_client, admin, exercise):
    source = make_plan(exercise)
    make_plan(exercise, source_plan=source)
    UserFavouritePlan.objects.create(user=admin, plan=source)

    response = admin_client.get(reverse("plan-list"), {"favourite": "true"})

    assert [plan["id"] for plan in response.json()] == [source.pk]
