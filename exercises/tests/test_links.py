from django.urls import reverse

from common.youtube import API_URL
from conftest import youtube_video
from exercises.models import ExerciseLink
from exercises.tests.helpers import make_exercise

VIDEO = "dQw4w9WgXcQ"
URL = f"https://youtu.be/{VIDEO}"


def add_url(exercise):
    return reverse("exercise-add-links", args=[exercise.pk])


def test_one_url_is_shared_and_youtube_is_asked_once(admin_client, exercise, youtube):
    other = make_exercise("Row")
    youtube.get(API_URL, json={"items": [youtube_video(VIDEO, title="Guide")]})

    first = admin_client.post(add_url(exercise), {"links": [URL]}, format="json")
    second = admin_client.post(add_url(other), {"links": [URL]}, format="json")

    assert first.status_code == second.status_code == 201
    assert second.json()[0]["title"] == "Guide"
    assert ExerciseLink.objects.count() == 1
    assert len(youtube.calls) == 1


def test_exercise_is_created_with_links(admin_client, youtube):
    response = admin_client.post(
        reverse("exercise-list"),
        {
            "name": "Squat",
            "description": "Sit and stand.",
            "muscle_categories": ["LEGS"],
            "load_category": "HEAVY",
            "intensity": 4,
            "links": ["https://a.com"],
        },
        format="json",
    )

    assert [link["url"] for link in response.json()["links"]] == ["https://a.com"]


def test_detaching_keeps_the_link_for_other_exercises(admin_client, exercise):
    other = make_exercise("Row")
    link = ExerciseLink.objects.create(url="https://a.com")
    exercise.links.add(link)
    other.links.add(link)

    response = admin_client.delete(reverse("exercise-delete-link", args=[exercise.pk, link.pk]))

    assert response.status_code == 204
    assert not exercise.links.exists()
    assert other.links.filter(pk=link.pk).exists()


def test_detached_link_row_stays(admin_client, exercise):
    link = ExerciseLink.objects.create(url="https://a.com")
    exercise.links.add(link)

    admin_client.delete(reverse("exercise-delete-link", args=[exercise.pk, link.pk]))

    assert ExerciseLink.objects.filter(pk=link.pk).exists()


def test_archived_exercise_links_are_read_only(admin_client, archived):
    link = ExerciseLink.objects.create(url="https://a.com")
    archived.links.add(link)

    added = admin_client.post(add_url(archived), {"links": ["https://b.com"]}, format="json")
    removed = admin_client.delete(reverse("exercise-delete-link", args=[archived.pk, link.pk]))

    assert added.status_code == removed.status_code == 409
    assert list(archived.links.all()) == [link]


def test_refresh_still_updates_an_archived_exercises_link(admin_client, archived, youtube):
    archived.links.add(ExerciseLink.objects.create(url=URL))
    youtube.get(API_URL, json={"items": [youtube_video(VIDEO, title="Guide")]})

    response = admin_client.post(reverse("exercise-refresh-links", args=[archived.pk]))

    assert response.status_code == 200
    assert ExerciseLink.objects.get(url=URL).title == "Guide"


def test_global_refresh_lists_a_gone_video_once_per_exercise(admin_client, exercise, youtube):
    other = make_exercise("Row")
    link = ExerciseLink.objects.create(url=URL)
    exercise.links.add(link)
    other.links.add(link)
    ExerciseLink.objects.create(url="https://youtu.be/AAAAAAAAAAA")  # attached to nothing, so no page to point to
    youtube.get(API_URL, json={"items": []})

    response = admin_client.post(reverse("refresh-links"))

    assert response.json() == {
        "filled": 0,
        "not_found": [
            {"url": URL, "type": "exercise", "object_id": exercise.pk},
            {"url": URL, "type": "exercise", "object_id": other.pk},
        ],
    }
