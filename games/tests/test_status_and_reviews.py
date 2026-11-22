import pytest
from django.urls import reverse

from games.models import GameStatus, PlayStatus


def status_url(game):
    return reverse("game-status", args=[game.pk])


def test_admin_sets_then_changes_own_status(admin_client, admin, game):
    admin_client.put(status_url(game), {"status": "PLANNED"}, format="json")

    response = admin_client.put(status_url(game), {"status": "DROPPED"}, format="json")

    assert response.status_code == 200
    assert response.json() == {"status": "DROPPED"}
    assert GameStatus.objects.get().user == admin
    assert GameStatus.objects.get().status == PlayStatus.DROPPED


def test_setting_status_keeps_other_admins_status(admin_client, friend, game):
    GameStatus.objects.create(game=game, user=friend, status=PlayStatus.PLAYING)

    admin_client.put(status_url(game), {"status": "COMPLETED"}, format="json")

    assert GameStatus.objects.get(user=friend).status == PlayStatus.PLAYING
    assert GameStatus.objects.count() == 2


def test_clearing_status_removes_only_own(admin_client, admin, friend, game):
    GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLANNED)
    GameStatus.objects.create(game=game, user=friend, status=PlayStatus.PLAYING)

    response = admin_client.delete(status_url(game))

    assert response.status_code == 204
    assert GameStatus.objects.get().user == friend


def test_clearing_missing_status_gives_204(admin_client, game):
    assert admin_client.delete(status_url(game)).status_code == 204


def test_invalid_status_is_refused(admin_client, game):
    response = admin_client.put(status_url(game), {"status": "FINISHED"}, format="json")

    assert response.status_code == 400
    assert not GameStatus.objects.exists()


def test_status_of_unknown_game_gives_404(admin_client, db):
    url = reverse("game-status", args=[999])

    assert admin_client.put(url, {"status": "PLANNED"}, format="json").status_code == 404
    assert admin_client.delete(url).status_code == 404


@pytest.mark.parametrize(
    ("client_name", "expected"),
    [
        ("user_client", 403),
        ("api_client", 401),
    ],
)
def test_only_admins_change_status(request, admin, game, client_name, expected):
    GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLANNED)
    client = request.getfixturevalue(client_name)

    assert client.put(status_url(game), {"status": "DROPPED"}, format="json").status_code == expected
    assert client.delete(status_url(game)).status_code == expected
    assert GameStatus.objects.get().status == PlayStatus.PLANNED


def test_admin_reviews_game_without_status(admin_client, game):
    response = admin_client.post(reverse("game-review", args=[game.pk]), {"rating": 9}, format="json")

    assert response.status_code == 201
    assert game.reviews.get().rating == 9


def test_user_cannot_review_game(user_client, game):
    response = user_client.post(reverse("game-review", args=[game.pk]), {"rating": 9}, format="json")

    assert response.status_code == 403
    assert not game.reviews.exists()
