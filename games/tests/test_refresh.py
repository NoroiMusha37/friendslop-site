from datetime import date

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from games.models import Game, GameCategory, GameReview, GameStatus, Genre, PlayStatus
from games.rawg import API_URL

REFRESH_ALL_URL = reverse("game-refresh-all")


def refresh_url(game):
    return reverse("game-refresh", args=[game.pk])


def rawg_reply(game, **overrides):
    """The game as RAWG sends it now."""
    return {
        "id": game.rawg_id,
        "name": "New name",
        "description_raw": "New description",
        "background_image": "https://media.rawg.io/new.jpg",
        "released": "2020-01-02",
        "rating": 3.5,
        "genres": [{"id": 7, "name": "Puzzle"}],
        **overrides,
    }


def add_game(rawg_id, name="Old name"):
    return Game.objects.create(rawg_id=rawg_id, name=name, categories=[GameCategory.SOLO])


def test_refresh_updates_rawg_data_and_keeps_ours(admin_client, admin, game, rawg):
    old_genre = Genre.objects.create(rawg_id=1, name="Old genre")
    game.genres.add(old_genre)
    GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLAYING)
    GameReview.objects.create(game=game, author=admin, rating=8)
    rawg.get(f"{API_URL}/{game.rawg_id}", json=rawg_reply(game))

    response = admin_client.post(refresh_url(game))

    assert response.status_code == 200
    data = response.json()
    assert data["not_found"] is False
    assert data["game"]["name"] == "New name"
    assert [genre["name"] for genre in data["game"]["genres"]] == ["Puzzle"]
    assert data["game"]["statuses"] == {"admin": "PLAYING"}
    assert data["game"]["ratings"] == {"admin": 8}
    game.refresh_from_db()
    assert game.description == "New description"
    assert game.cover_url == "https://media.rawg.io/new.jpg"
    assert game.release_date == date(2020, 1, 2)
    assert game.rawg_rating == 3.5
    assert game.categories == ["SOLO"]


def test_refresh_clears_what_rawg_no_longer_has(admin_client, rawg, db):
    game = Game.objects.create(
        rawg_id=1,
        name="Game",
        description="Text",
        cover_url="https://media.rawg.io/old.jpg",
        release_date=date(2000, 1, 1),
        rawg_rating=4.0,
        categories=[GameCategory.SOLO],
    )
    game.genres.add(Genre.objects.create(rawg_id=1, name="Action"))
    rawg.get(
        f"{API_URL}/1",
        json=rawg_reply(
            game,
            description_raw=None,
            background_image=None,
            released=None,
            rating=0,
            genres=None,
        ),
    )

    admin_client.post(refresh_url(game))

    game.refresh_from_db()
    assert (game.description, game.cover_url, game.release_date, game.rawg_rating) == ("", "", None, None)
    assert not game.genres.exists()


def test_refresh_of_game_rawg_no_longer_has(admin_client, game, rawg):
    rawg.get(f"{API_URL}/{game.rawg_id}", status=404)

    response = admin_client.post(refresh_url(game))

    assert response.status_code == 200
    assert response.json()["not_found"] is True
    assert response.json()["game"]["name"] == "Portal"


def test_refresh_all_updates_found_and_reports_missing(admin_client, rawg, db):
    first = add_game(1)
    gone = add_game(2, "Gone")
    last = add_game(3)
    rawg.get(f"{API_URL}/1", json=rawg_reply(first, name="First"))
    rawg.get(f"{API_URL}/2", status=404)
    rawg.get(f"{API_URL}/3", json=rawg_reply(last, name="Last", genres=[{"id": 8, "name": "Action"}]))

    response = admin_client.post(REFRESH_ALL_URL)

    assert response.json() == {
        "updated": 2,
        "not_found": [{"id": gone.pk, "name": "Gone"}],
    }
    assert list(Game.objects.order_by("id").values_list("name", flat=True)) == ["First", "Gone", "Last"]
    assert first.genres.get().name == "Puzzle"
    assert last.genres.get().name == "Action"


def test_rawg_failure_midway_changes_nothing(admin_client, rawg, db):
    first = add_game(1)
    add_game(2)
    rawg.get(f"{API_URL}/1", json=rawg_reply(first))
    rawg.get(f"{API_URL}/2", status=500, json={})

    response = admin_client.post(REFRESH_ALL_URL)

    assert response.status_code == 503
    assert set(Game.objects.values_list("name", flat=True)) == {"Old name"}
    assert not Genre.objects.exists()


def test_refresh_all_queries_dont_grow_with_games(admin_client, rawg, db):
    def add_with_reply(rawg_id):
        game = add_game(rawg_id)
        rawg.get(f"{API_URL}/{rawg_id}", json=rawg_reply(game))

    for rawg_id in range(1, 3):
        add_with_reply(rawg_id)
    with CaptureQueriesContext(connection) as few_games:
        admin_client.post(REFRESH_ALL_URL)
    for rawg_id in range(3, 13):
        add_with_reply(rawg_id)
    Genre.objects.all().delete()  # so both runs create the genre
    with CaptureQueriesContext(connection) as many_games:
        admin_client.post(REFRESH_ALL_URL)

    assert len(many_games) == len(few_games)


def test_refresh_of_unknown_game_gives_404(admin_client, rawg, db):
    assert admin_client.post(reverse("game-refresh", args=[999])).status_code == 404


def test_regular_user_cant_refresh(user_client, game, rawg):
    assert user_client.post(refresh_url(game)).status_code == 403
    assert user_client.post(REFRESH_ALL_URL).status_code == 403
