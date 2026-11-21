import pytest
from django.db import IntegrityError

from games.models import Game, GameCategory, GameReview, GameStatus, PlayStatus


def test_game_needs_a_category(db):
    with pytest.raises(IntegrityError):
        Game.objects.create(
            rawg_id=1,
            name="No category",
            categories=[],
        )


@pytest.mark.parametrize("rating", [0, 5.01])
def test_rawg_rating_outside_range_is_refused(db, rating):
    # 0 must be stored as null, otherwise unrated games would sort as the worst ones
    with pytest.raises(IntegrityError):
        Game.objects.create(
            rawg_id=1,
            name="Bad rating",
            rawg_rating=rating,
            categories=[GameCategory.SOLO],
        )


def test_game_can_have_no_rawg_rating(db):
    game = Game.objects.create(
        rawg_id=1,
        name="Unrated",
        rawg_rating=None,
        categories=[GameCategory.SOLO],
    )

    game.refresh_from_db()
    assert game.rawg_rating is None


def test_admin_has_one_status_per_game(game, admin):
    GameStatus.objects.create(
        game=game,
        user=admin,
        status=PlayStatus.PLANNED,
    )

    with pytest.raises(IntegrityError):
        GameStatus.objects.create(
            game=game,
            user=admin,
            status=PlayStatus.DROPPED,
        )


def test_admin_reviews_game_only_once(game, admin):
    GameReview.objects.create(
        game=game,
        author=admin,
        rating=8,
    )

    with pytest.raises(IntegrityError):
        GameReview.objects.create(
            game=game,
            author=admin,
            rating=3,
        )
