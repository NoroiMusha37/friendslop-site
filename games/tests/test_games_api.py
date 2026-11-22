import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from games.models import Game, GameCategory, GameReview, GameStatus, Genre, PlayStatus

LIST_URL = reverse("game-list")


def detail_url(game):
    return reverse("game-detail", args=[game.pk])


def add_game(rawg_id, name="Game", rawg_rating=None, categories=(GameCategory.SOLO,)):
    return Game.objects.create(
        rawg_id=rawg_id,
        name=name,
        rawg_rating=rawg_rating,
        categories=list(categories),
    )


def names(response):
    assert response.status_code == 200
    return [game["name"] for game in response.json()]


def test_list_shows_statuses_and_ratings_per_admin(user_client, admin, friend, game):
    genre = Genre.objects.create(rawg_id=4, name="Puzzle")
    game.genres.add(genre)
    GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLAYING)
    GameReview.objects.create(game=game, author=admin, rating=6)
    GameReview.objects.create(game=game, author=friend, rating=9)

    response = user_client.get(LIST_URL)

    assert response.json() == [
        {
            "id": game.pk,
            "name": "Portal",
            "cover_url": "",
            "release_date": None,
            "rawg_rating": 4.48,
            "categories": ["SOLO"],
            "genres": [{"id": genre.pk, "name": "Puzzle"}],
            "statuses": {"admin": "PLAYING", "friend": None},
            "ratings": {"admin": 6, "friend": 9},
            "combined_rating": 7.5,
        },
    ]


def test_detail_adds_description_and_reviews(user_client, admin, game):
    review = GameReview.objects.create(game=game, author=admin, rating=6, text="Fun")

    data = user_client.get(detail_url(game)).json()

    assert data["description"] == ""
    assert data["reviews"] == [{"id": review.pk, "author": "admin", "rating": 6, "text": "Fun"}]


def test_list_is_newest_first(user_client, db):
    add_game(1, "Old")
    add_game(2, "New")

    assert names(user_client.get(LIST_URL)) == ["New", "Old"]


def test_filter_by_genre_category_and_search(user_client, db):
    action = Genre.objects.create(rawg_id=4, name="Action")
    match = add_game(1, "Doom Eternal", categories=[GameCategory.SOLO, GameCategory.COOP])
    match.genres.add(action)
    add_game(2, "Doom Classic", categories=[GameCategory.SOLO]).genres.add(action)
    add_game(3, "Eternal Coop", categories=[GameCategory.COOP])

    assert names(user_client.get(LIST_URL, {"genre": action.pk, "category": "COOP"})) == ["Doom Eternal"]
    assert names(user_client.get(LIST_URL, {"search": "doom"})) == ["Doom Classic", "Doom Eternal"]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"status": "PLANNED"}, ["Both", "Mine"]),
        ({"status": "PLANNED", "admin": "friend"}, ["Both"]),
        # Friend has this game, but as DROPPED: the status and the admin must match one row
        ({"status": "DROPPED", "admin": "admin"}, []),
        ({"admin": "friend"}, ["Friend dropped", "Both"]),
    ],
)
def test_filter_by_status_and_admin(user_client, admin, friend, params, expected):
    mine = add_game(1, "Mine")
    both = add_game(2, "Both")
    dropped = add_game(3, "Friend dropped")
    add_game(4, "Nobody")
    GameStatus.objects.create(game=mine, user=admin, status=PlayStatus.PLANNED)
    GameStatus.objects.create(game=both, user=admin, status=PlayStatus.PLANNED)
    GameStatus.objects.create(game=both, user=friend, status=PlayStatus.PLANNED)
    GameStatus.objects.create(game=dropped, user=admin, status=PlayStatus.PLAYING)
    GameStatus.objects.create(game=dropped, user=friend, status=PlayStatus.DROPPED)

    assert names(user_client.get(LIST_URL, params)) == expected


def test_filter_by_regular_user_as_admin_is_refused(user_client, user):
    assert user_client.get(LIST_URL, {"admin": user.username}).status_code == 400


def test_filters_dont_change_combined_rating(user_client, admin, friend, game):
    GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLANNED)
    GameStatus.objects.create(game=game, user=friend, status=PlayStatus.PLANNED)
    GameReview.objects.create(game=game, author=admin, rating=4)
    GameReview.objects.create(game=game, author=friend, rating=8)

    response = user_client.get(LIST_URL, {"status": "PLANNED"})

    assert response.json()[0]["combined_rating"] == 6.0


def test_ordering_by_rawg_rating_puts_unrated_last(user_client, db):
    add_game(1, "Low", rawg_rating=2.0)
    add_game(2, "High", rawg_rating=4.5)
    add_game(3, "Unrated")

    assert names(user_client.get(LIST_URL, {"ordering": "-rawg_rating"})) == ["High", "Low", "Unrated"]
    assert names(user_client.get(LIST_URL, {"ordering": "rawg_rating"})) == ["Low", "High", "Unrated"]


def test_ordering_by_admin_rating(user_client, admin, db):
    low = add_game(1, "Low")
    high = add_game(2, "High")
    add_game(3, "Unrated")
    GameReview.objects.create(game=low, author=admin, rating=2)
    GameReview.objects.create(game=high, author=admin, rating=9)

    assert names(user_client.get(LIST_URL, {"ordering": "-rating:admin"})) == ["High", "Low", "Unrated"]


def test_genres_lists_only_used_ones_by_name_once(user_client, db):
    used = Genre.objects.create(rawg_id=1, name="Strategy")
    also_used = Genre.objects.create(rawg_id=2, name="Action")
    Genre.objects.create(rawg_id=3, name="Unused")
    add_game(1).genres.add(used, also_used)
    add_game(2).genres.add(used)

    response = user_client.get(reverse("game-genres"))

    assert [genre["name"] for genre in response.json()] == ["Action", "Strategy"]


def test_admin_edits_categories(admin_client, game):
    response = admin_client.patch(
        detail_url(game),
        {"categories": ["COOP", "COOP", "MULTIPLAYER"]},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["categories"] == ["COOP", "MULTIPLAYER"]
    game.refresh_from_db()
    assert game.categories == ["COOP", "MULTIPLAYER"]


@pytest.mark.parametrize("data", [{}, {"categories": []}, {"categories": ["RACING"]}])
def test_invalid_categories_are_refused(admin_client, game, data):
    assert admin_client.patch(detail_url(game), data, format="json").status_code == 400
    game.refresh_from_db()
    assert game.categories == ["SOLO"]


def test_patch_changes_only_categories(admin_client, game):
    admin_client.patch(detail_url(game), {"categories": ["COOP"], "name": "Changed"}, format="json")

    game.refresh_from_db()
    assert game.name == "Portal"


def test_admin_deletes_game_with_its_statuses_and_reviews(admin_client, admin, game):
    GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLANNED)
    GameReview.objects.create(game=game, author=admin, rating=6)

    assert admin_client.delete(detail_url(game)).status_code == 204
    assert not Game.objects.exists()
    assert not GameStatus.objects.exists()
    assert not GameReview.objects.exists()


def test_regular_user_reads_but_cant_change_games(user_client, game):
    assert user_client.get(detail_url(game)).status_code == 200
    assert user_client.patch(detail_url(game), {"categories": ["COOP"]}, format="json").status_code == 403
    assert user_client.delete(detail_url(game)).status_code == 403
    assert Game.objects.get().categories == ["SOLO"]


def test_logged_out_visitor_cant_read_games(api_client, game):
    assert api_client.get(LIST_URL).status_code == 401
    assert api_client.get(detail_url(game)).status_code == 401
    assert api_client.get(reverse("game-genres")).status_code == 401


def test_list_queries_dont_grow_with_games(user_client, admin, friend):
    genre = Genre.objects.create(rawg_id=1, name="Action")

    def add_full_games(first_id, count):
        for rawg_id in range(first_id, first_id + count):
            game = add_game(rawg_id)
            game.genres.add(genre)
            GameStatus.objects.create(game=game, user=admin, status=PlayStatus.PLANNED)
            GameReview.objects.create(game=game, author=friend, rating=5)

    add_full_games(1, 2)
    with CaptureQueriesContext(connection) as few_games:
        user_client.get(LIST_URL)
    add_full_games(3, 10)
    with CaptureQueriesContext(connection) as many_games:
        user_client.get(LIST_URL)

    assert len(many_games) == len(few_games)
