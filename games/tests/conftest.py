import pytest

from games.models import Game, GameCategory


@pytest.fixture
def game(db):
    return Game.objects.create(
        rawg_id=13536,
        name="Portal",
        rawg_rating=4.48,
        categories=[GameCategory.SOLO],
    )
