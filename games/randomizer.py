from django.db.models import Exists, OuterRef

from accounts.models import User
from games.models import Game, GameStatus
from games.schemas import RandomGameQuery


def pick_game_id(query: RandomGameQuery, user: User) -> int | None:
    """A random matching game's id, or None if nothing matches."""
    games = Game.objects.all()
    if query.genre is not None:
        games = games.filter(genres=query.genre)
    if query.category is not None:
        games = games.filter(categories__contains=[query.category])

    admins = [user] if query.status_scope == "mine" else User.objects.filter(is_superuser=True)
    for admin in admins:
        games = games.filter(
            Exists(GameStatus.objects.filter(game=OuterRef("pk"), user=admin, status=query.status)),
        )
    return games.order_by("?").values_list("pk", flat=True).first()
