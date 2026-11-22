import pytest
from django.urls import reverse

from games.models import Game, GameCategory, GameReview, GameStatus, Genre, PlayStatus

URL = reverse("game-random")


def add_game(rawg_id, name, categories=(GameCategory.SOLO,)):
    return Game.objects.create(rawg_id=rawg_id, name=name, categories=list(categories))


def set_status(game, user, status=PlayStatus.PLANNED):
    GameStatus.objects.create(game=game, user=user, status=status)


def pick(client, **params):
    response = client.get(URL, {"status": "PLANNED", "status_scope": "mine", **params})
    assert response.status_code == 200
    return response.json()["name"]


@pytest.mark.parametrize("status", PlayStatus.values)
def test_mine_picks_from_any_of_my_statuses(admin_client, admin, friend, status):
    set_status(add_game(1, "Mine"), admin, status)
    set_status(add_game(2, "Friend's"), friend, status)
    other = "PLAYING" if status != "PLAYING" else "DROPPED"
    set_status(add_game(3, "Other status"), admin, other)

    for _ in range(10):
        assert pick(admin_client, status=status) == "Mine"


def test_both_needs_the_same_status_from_both_admins(admin_client, admin, friend):
    both = add_game(1, "Both")
    set_status(both, admin)
    set_status(both, friend)
    set_status(add_game(2, "Only mine"), admin)
    set_status(add_game(3, "Only friend's"), friend)
    different = add_game(4, "Different")
    set_status(different, admin)
    set_status(different, friend, PlayStatus.DROPPED)

    for _ in range(10):
        assert pick(admin_client, status_scope="both") == "Both"


def test_genre_and_category_narrow_the_pick(admin_client, admin):
    action = Genre.objects.create(rawg_id=1, name="Action")
    match = add_game(1, "Match", [GameCategory.SOLO, GameCategory.COOP])
    match.genres.add(action)
    wrong_category = add_game(2, "Wrong category")
    wrong_category.genres.add(action)
    wrong_genre = add_game(3, "Wrong genre", [GameCategory.COOP])
    for game in (match, wrong_category, wrong_genre):
        set_status(game, admin)

    for _ in range(10):
        assert pick(admin_client, genre=action.pk, category="COOP") == "Match"


def test_every_matching_game_can_be_picked(admin_client, admin):
    set_status(add_game(1, "First"), admin)
    set_status(add_game(2, "Second"), admin)

    assert {pick(admin_client) for _ in range(50)} == {"First", "Second"}


def test_empty_filters_are_ignored(admin_client, admin):
    set_status(add_game(1, "Only"), admin)

    assert pick(admin_client, genre="", category="") == "Only"


def test_pick_has_the_detail_shape(admin_client, admin):
    game = add_game(1, "Only")
    set_status(game, admin)
    GameReview.objects.create(game=game, author=admin, rating=7)

    data = admin_client.get(URL, {"status": "PLANNED", "status_scope": "mine"}).json()

    assert data["description"] == ""
    assert data["statuses"] == {"admin": "PLANNED"}
    assert data["reviews"][0]["rating"] == 7


def test_nothing_matching_gives_404(admin_client, friend):
    set_status(add_game(1, "Friend's"), friend)

    response = admin_client.get(URL, {"status": "PLANNED", "status_scope": "mine"})

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"status_scope": "mine"}, "status"),
        ({"status": "PLANNED"}, "status_scope"),
        ({"status": "FINISHED", "status_scope": "mine"}, "status"),
        ({"status": "PLANNED", "status_scope": "everyone"}, "status_scope"),
        ({"status": "PLANNED", "status_scope": "mine", "category": "RACING"}, "category"),
        ({"status": "PLANNED", "status_scope": "mine", "genre": "action"}, "genre"),
        ({"status": "PLANNED", "status_scope": "mine", "genre": 999}, "genre"),
    ],
)
def test_invalid_query_is_refused(admin_client, params, field):
    response = admin_client.get(URL, params)

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize(
    ("client_name", "expected"),
    [
        ("user_client", 403),
        ("api_client", 401),
    ],
)
def test_only_admins_use_the_randomizer(request, db, client_name, expected):
    client = request.getfixturevalue(client_name)

    assert client.get(URL, {"status": "PLANNED", "status_scope": "mine"}).status_code == expected
