# games

## Purpose

The shared game backlog: games copied from RAWG (an external game database), each admin's status and reviews.

## Ownership

- `models.py`: `Genre`, `Game`, `GameStatus`, `GameReview`, and the `GameCategory` and `PlayStatus` choices
- `admin.py`: Django admin page for games

## Local Contracts

- Games come only from RAWG. Only `categories` is ours (at least one, set by admins)
- RAWG reports unrated games as 0; store that as a null `rawg_rating`, the database refuses 0
- Each admin has at most one status and one review per game
- Django admin: view and delete games and edit categories; adding games and changing RAWG data are blocked

## Work Guidance

## Verification

- `docker compose run --rm web pytest games`

## Child DOX Index

None.
