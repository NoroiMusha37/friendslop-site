from django.db import transaction

from games.models import Game, Genre
from games.schemas import RawgGame


def create_game(rawg_game: RawgGame, categories: list[str]) -> Game:
    genres = rawg_game.genres or []
    with transaction.atomic():
        game = Game.objects.create(
            rawg_id=rawg_game.id,
            name=rawg_game.name,
            description=rawg_game.description_raw or "",
            cover_url=rawg_game.background_image or "",
            release_date=rawg_game.released,
            rawg_rating=rawg_game.rawg_rating,
            categories=categories,
        )
        # Genres are shared between games, so the ones already saved are skipped
        Genre.objects.bulk_create(
            [Genre(rawg_id=genre.id, name=genre.name) for genre in genres],
            ignore_conflicts=True,
        )
        game.genres.set(Genre.objects.filter(rawg_id__in=[genre.id for genre in genres]))
    return game
