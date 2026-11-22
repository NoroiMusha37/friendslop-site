from django.db import transaction

from games.models import Game, Genre
from games.rawg import get_game
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


def refresh_games(games: list[Game]) -> tuple[int, list[Game]]:
    """Copies RAWG's current data into `games`. Returns how many were updated and the games RAWG no longer has.

    Every reply is collected before saving, so a RAWG failure midway changes nothing.
    """
    replies = [(game, get_game(game.rawg_id)) for game in games]
    found = [(game, rawg_game) for game, rawg_game in replies if rawg_game is not None]
    for game, rawg_game in found:
        game.name = rawg_game.name
        game.description = rawg_game.description_raw or ""
        game.cover_url = rawg_game.background_image or ""
        game.release_date = rawg_game.released
        game.rawg_rating = rawg_game.rawg_rating

    names = {genre.id: genre.name for _, rawg_game in found for genre in rawg_game.genres or []}
    links = Game.genres.through
    with transaction.atomic():
        Game.objects.bulk_update(
            [game for game, _ in found],
            ["name", "description", "cover_url", "release_date", "rawg_rating"],
        )
        # Genres are shared between games, so the ones already saved are skipped
        Genre.objects.bulk_create(
            [Genre(rawg_id=rawg_id, name=name) for rawg_id, name in names.items()],
            ignore_conflicts=True,
        )
        genre_ids = dict(Genre.objects.filter(rawg_id__in=names).values_list("rawg_id", "id"))
        links.objects.filter(game__in=[game for game, _ in found]).delete()
        links.objects.bulk_create(
            [
                links(game=game, genre_id=genre_ids[genre.id])
                for game, rawg_game in found
                for genre in rawg_game.genres or []
            ],
            ignore_conflicts=True,  # RAWG could list a genre twice
        )
    return len(found), [game for game, rawg_game in replies if rawg_game is None]
