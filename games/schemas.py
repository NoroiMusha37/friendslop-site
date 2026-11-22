from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints, field_validator

from games.models import GameCategory, PlayStatus


class GameSearchQuery(BaseModel):
    q: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]


class RandomGameQuery(BaseModel):
    """Query parameters of `GET /games/random/`."""

    status: PlayStatus
    status_scope: Literal["mine", "both"]
    genre: int | None = None
    category: GameCategory | None = None

    @field_validator("genre", "category", mode="before")
    @classmethod
    def empty_means_no_filter(cls, value):
        return None if value == "" else value


class RawgGenre(BaseModel):
    id: int
    name: str


class RawgGame(BaseModel):
    """A game as RAWG sends it; everything except the id and name can be missing or null."""

    id: int
    name: str
    description_raw: str | None = None
    background_image: str | None = None
    released: date | None = None
    rating: float | None = None
    genres: list[RawgGenre] | None = None

    @property
    def rawg_rating(self) -> float | None:
        # RAWG reports unrated games as 0
        return self.rating or None


class RawgGameList(BaseModel):
    results: list[RawgGame]
