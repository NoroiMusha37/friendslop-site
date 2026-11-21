import pytest
import responses

from games.models import Game, GameCategory


@pytest.fixture
def rawg(settings):
    """Fake RAWG API: register replies with `rawg.get(API_URL, ...)`; real requests are blocked."""
    settings.RAWG_API_KEY = "test-key"
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture
def game(db):
    return Game.objects.create(
        rawg_id=13536,
        name="Portal",
        rawg_rating=4.48,
        categories=[GameCategory.SOLO],
    )
