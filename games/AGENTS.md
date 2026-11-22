# games

## Purpose

The shared game backlog: games copied from RAWG (an external game database), each admin's status and reviews.

## Ownership

- `models.py`: `Genre`, `Game`, `GameStatus`, `GameReview`, and the `GameCategory` and `PlayStatus` choices
- `rawg.py` + `schemas.py`: RAWG client, its `RawgError` and reply shapes
- `views.py`, `urls.py`, `serializers.py`: RAWG search, games (add, list, detail, edit categories, delete), genres, each admin's status and review (`/api/v1/games/`)
- `filters.py`: list filters, search and sorting
- `services.py`: saves a game and its genres from RAWG data
- `admin.py`: Django admin page for games

## Local Contracts

- Games come only from RAWG. Only `categories` is ours (at least one, set by admins)
- RAWG reports unrated games as 0; store that as a null `rawg_rating`, the database refuses 0
- Each admin has at most one status and one review per game
- Django admin: view and delete games, edit categories, statuses and reviews; adding games and changing RAWG data are blocked
- RAWG failures answer 503 with a `detail` saying what went wrong and save nothing. The request URL contains the key, so it is never logged
- Tests never call RAWG: they use the `rawg` fixture in `games/tests/conftest.py`

## Work Guidance

## Verification

- `docker compose run --rm web pytest games`

## Child DOX Index

None.
