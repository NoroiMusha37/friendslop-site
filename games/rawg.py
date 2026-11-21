"""RAWG API client: searches games and fetches one game. Every failure says what went wrong."""

import logging

import requests
from django.conf import settings
from pydantic import BaseModel
from rest_framework.exceptions import APIException

from games.schemas import RawgGame, RawgGameList

logger = logging.getLogger(__name__)

API_URL = "https://api.rawg.io/api/games"
SEARCH_SIZE = 10
TIMEOUT_SECONDS = 5
UNAVAILABLE = "RAWG is unavailable right now. Try again later."


class RawgError(APIException):
    status_code = 503


def _fetch[T: BaseModel](schema: type[T], url: str, params: dict | None = None) -> T | None:
    """The parsed reply, or None if RAWG has no such object. Logs never include the URL: it contains the key."""
    try:
        response = requests.get(
            url,
            params={**(params or {}), "key": settings.RAWG_API_KEY},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout as e:
        logger.warning("RAWG timed out (%s)", type(e).__name__)
        raise RawgError("RAWG took too long to answer. Try again.") from e
    except requests.RequestException as e:
        logger.warning("RAWG unreachable (%s)", type(e).__name__)
        raise RawgError(UNAVAILABLE) from e

    if response.status_code == 404:
        return None
    if response.status_code == 429 or (response.status_code in (401, 403) and "limit" in response.text.lower()):
        logger.warning("RAWG request limit reached: HTTP %s", response.status_code)
        raise RawgError("The RAWG request limit is used up.")
    if response.status_code in (401, 403):
        logger.error("RAWG API key rejected: HTTP %s", response.status_code)
        raise RawgError("RAWG rejected the API key. Check RAWG_API_KEY.")
    if response.status_code != 200:
        logger.warning("RAWG unavailable: HTTP %s", response.status_code)
        raise RawgError(UNAVAILABLE)

    try:
        return schema.model_validate(response.json())
    except ValueError as e:  # not JSON, or not the expected shape
        logger.warning("RAWG sent an unexpected reply (%s)", type(e).__name__)
        raise RawgError(UNAVAILABLE) from e


def search_games(query: str) -> list[RawgGame]:
    page = _fetch(
        RawgGameList,
        API_URL,
        {"search": query, "page_size": SEARCH_SIZE},
    )
    return page.results if page else []


def get_game(rawg_id: int) -> RawgGame | None:
    return _fetch(RawgGame, f"{API_URL}/{rawg_id}")
