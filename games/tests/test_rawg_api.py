import json

import pytest
import requests
from django.urls import reverse
from responses import matchers

from games.models import Game, GameCategory, Genre
from games.rawg import API_URL

SEARCH_URL = "game-search"
CREATE_URL = "game-list"


def rawg_game(rawg_id=4200, **overrides):
    """One game as RAWG sends it."""
    return {
        "id": rawg_id,
        "name": "Portal 2",
        "description_raw": "Puzzles.",
        "background_image": "https://media.rawg.io/portal2.jpg",
        "released": "2011-04-18",
        "rating": 4.6,
        "genres": [{"id": 7, "name": "Puzzle"}],
        **overrides,
    }


def add_game(client, rawg_id=4200, categories=("SOLO",)):
    return client.post(
        reverse(CREATE_URL),
        {"rawg_id": rawg_id, "categories": list(categories)},
        format="json",
    )


def test_search_returns_top_results_and_marks_added_games(admin_client, game, rawg):
    rawg.get(
        API_URL,
        match=[matchers.query_param_matcher({"search": "portal", "page_size": "10", "key": "test-key"})],
        json={
            "results": [
                rawg_game(game.rawg_id, name="Portal"),
                rawg_game(background_image=None, released=None, rating=0, genres=[]),
            ],
        },
    )

    response = admin_client.get(reverse(SEARCH_URL), {"q": " portal "})

    assert response.status_code == 200
    assert response.json() == [
        {
            "rawg_id": game.rawg_id,
            "game_id": game.pk,
            "name": "Portal",
            "cover_url": "https://media.rawg.io/portal2.jpg",
            "release_date": "2011-04-18",
            "rawg_rating": 4.6,
            "genres": ["Puzzle"],
        },
        {
            "rawg_id": 4200,
            "game_id": None,
            "name": "Portal 2",
            "cover_url": "",
            "release_date": None,
            "rawg_rating": None,
            "genres": [],
        },
    ]


@pytest.mark.parametrize("params", [{}, {"q": "a"}, {"q": " a "}])
def test_search_needs_two_characters(admin_client, rawg, params):
    response = admin_client.get(reverse(SEARCH_URL), params)

    assert response.status_code == 400
    assert "q" in response.json()
    assert len(rawg.calls) == 0


def test_regular_user_cant_search(user_client, rawg):
    response = user_client.get(reverse(SEARCH_URL), {"q": "portal"})

    assert response.status_code == 403
    assert len(rawg.calls) == 0


@pytest.mark.parametrize(
    ("reply", "message"),
    [
        ({"body": requests.Timeout()}, "RAWG took too long to answer. Try again."),
        ({"body": requests.ConnectionError()}, "RAWG is unavailable right now. Try again later."),
        ({"status": 500, "json": {"results": []}}, "RAWG is unavailable right now. Try again later."),
        ({"body": "not json"}, "RAWG is unavailable right now. Try again later."),
        ({"json": {"unexpected": True}}, "RAWG is unavailable right now. Try again later."),
        (
            {"status": 401, "json": {"error": "The API key is not found"}},
            "RAWG rejected the API key. Check RAWG_API_KEY.",
        ),
        (
            {"status": 401, "json": {"error": "The monthly API limit reached."}},
            "The RAWG request limit is used up.",
        ),
        ({"status": 429}, "The RAWG request limit is used up."),
    ],
)
def test_rawg_failure_says_what_went_wrong(admin_client, rawg, reply, message):
    rawg.get(API_URL, **reply)

    response = admin_client.get(reverse(SEARCH_URL), {"q": "portal"})

    assert response.status_code == 503
    assert response.json() == {"detail": message}


def test_admin_adds_game_from_rawg(admin_client, rawg):
    rawg.get(f"{API_URL}/4200", json=rawg_game())

    response = add_game(admin_client, categories=["COOP", "SOLO", "COOP"])

    assert response.status_code == 201
    game = Game.objects.get(rawg_id=4200)
    assert response.json() == {
        "id": game.pk,
        "name": "Portal 2",
        "description": "Puzzles.",
        "cover_url": "https://media.rawg.io/portal2.jpg",
        "release_date": "2011-04-18",
        "rawg_rating": 4.6,
        "categories": ["COOP", "SOLO"],
        "genres": [{"id": game.genres.get().pk, "name": "Puzzle"}],
    }


def test_game_with_missing_rawg_data_is_saved_empty(admin_client, rawg):
    rawg.get(
        f"{API_URL}/4200",
        json=rawg_game(
            description_raw=None,
            background_image=None,
            released=None,
            rating=0,
            genres=None,
        ),
    )

    response = add_game(admin_client)

    assert response.status_code == 201
    game = Game.objects.get(rawg_id=4200)
    assert game.description == ""
    assert game.cover_url == ""
    assert game.release_date is None
    assert game.rawg_rating is None
    assert not game.genres.exists()


def test_games_share_a_genre(admin_client, rawg):
    rawg.get(f"{API_URL}/4200", json=rawg_game())
    rawg.get(f"{API_URL}/4201", json=rawg_game(4201))

    add_game(admin_client, 4200)
    add_game(admin_client, 4201)

    assert Genre.objects.get(rawg_id=7).games.count() == 2


def test_adding_a_game_twice_points_to_the_existing_one(admin_client, game, rawg):
    response = add_game(admin_client, game.rawg_id)

    assert response.status_code == 409
    assert response.json()["game_id"] == game.pk
    assert len(rawg.calls) == 0


def test_double_click_gives_the_same_conflict(admin_client, rawg):
    def other_request_saves_first(request):
        Game.objects.create(
            rawg_id=4200,
            name="Portal 2",
            categories=[GameCategory.SOLO],
        )
        return 200, {}, json.dumps(rawg_game())

    rawg.add_callback(rawg.GET, f"{API_URL}/4200", callback=other_request_saves_first)

    response = add_game(admin_client)

    assert response.status_code == 409
    assert response.json()["game_id"] == Game.objects.get(rawg_id=4200).pk


def test_unknown_rawg_game_is_refused(admin_client, rawg):
    rawg.get(f"{API_URL}/4200", status=404)

    response = add_game(admin_client)

    assert response.status_code == 400
    assert "rawg_id" in response.json()
    assert not Game.objects.exists()


def test_rawg_failure_saves_nothing(admin_client, rawg):
    rawg.get(f"{API_URL}/4200", status=500)

    response = add_game(admin_client)

    assert response.status_code == 503
    assert not Game.objects.exists()


@pytest.mark.parametrize("categories", [[], ["WRONG"]])
def test_add_needs_valid_categories(admin_client, rawg, categories):
    response = add_game(admin_client, categories=categories)

    assert response.status_code == 400
    assert "categories" in response.json()
    assert len(rawg.calls) == 0


def test_regular_user_cant_add_game(user_client, rawg):
    response = add_game(user_client)

    assert response.status_code == 403
    assert not Game.objects.exists()
