# common

## Purpose

Code shared by recipes, games and exercises: links with YouTube info, admin reviews and ratings.

## Ownership

- `models.py`: abstract `BaseLink` and `BaseReview`; each app adds its target and a one-review-per-author constraint
- `serializers.py`: `LinkSerializer`, `AddLinksSerializer`, `ReviewSerializer`, `RatingsMixin`
- `views.py`: `LinksMixin` (add, refresh, delete links), `ReviewsMixin` (own review: POST / PATCH / DELETE), `RefreshLinksView` (`/api/v1/links/refresh/`, routed in `urls.py`)
- `admin.py`: `AdminOwnerInline`, limits an inline's owner dropdown to admins
- `links.py`: link checks, saving and filling missing YouTube info; `youtube.py` + `schemas.py`: YouTube Data API client
- `ratings.py`, `filters.py`: combined rating and sorting by rating
- `query.py`: `parse_query`, checks query parameters with a pydantic schema and answers DRF's usual 400 (used by the randomizers)

## Local Contracts

- Everything here works with any model whose objects have `links` / `reviews`; never write app-specific code here
- Mixins take their permissions from the viewset that uses them; a viewset can refuse link and review writes by overriding `check_owner_writable`
- `links` can be a reverse foreign key (one owner, removing deletes the row) or many-to-many (shared rows, one per url; removing drops only the relation)
- YouTube info for all links of a request is fetched in one call. YouTube down: links saved without info, filled in later by the refresh endpoints. Invalid API key: 503, nothing saved
- Tests never call YouTube: they use the root `youtube` fixture (`responses`)

## Work Guidance

## Verification

- `docker compose run --rm web pytest common recipes exercises` (the mixins are exercised through the recipe and exercise endpoints)

## Child DOX Index

None.
