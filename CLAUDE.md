# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Facts
Every time you get new information about this project, or new way of interaction with 
library/models/services, or specific instructions from user on how to test/implement new feature,
add short description of acquired knowledge here in bulleted list:
- Before starting any step: analyze the plan for that step first, report all inconsistencies, and ask EVERYTHING that needs clarification or the user's decision. Write code only after all of that is resolved. Never silently pick defaults.
- Add dependencies and settings only in the step that first uses them; no unused packages or settings variables.
- Settings are read with `pydantic-settings`. Database connection is built from the same `POSTGRES_*` variables Docker Compose uses (no `DATABASE_URL`). `TIME_ZONE = "Europe/Kyiv"`.
- Everything runs in Docker (Django + PostgreSQL 18) via Docker Compose, including tests.
- Django apps live in the repo root (next to `config/`); each app is created (`startapp`, generated stubs are fine) in the phase that first uses it. API URLs are under `/api/v1/`: each prefix is written once in `config/urls.py`; a new app adds one line to the `api_v1` list. Never repeat a path prefix in any urls.py: group paths under one `include([...])` per prefix (e.g. `auth/` in `accounts/urls.py`). pytest uses `importmode = "importlib"` (no `__init__.py` in `tests/` folders).
- Ruff is not in CI: the agent runs `ruff check .` and `ruff format --check .` (in Docker) after each step, before proposing a commit/merge. Unused imports in `startapp` stubs are left as they are. `migrations/` folders are excluded from ruff.
- Users: admin = `is_superuser` (only the two team superusers, created with `createsuperuser`, which sets `approved_at`). Pending = `approved_at` is null. Rejecting a sign-up deletes the account. `first_name`/`last_name` removed; `last_login`/`date_joined` kept. User is registered in the Django admin panel.
- Lists filtering uses `django-filter`, added with the first filtered list (users `?status=` in Phase 1); never hand-write filters it covers.
- Django 6.1 is kept even though simplejwt 5.5.1 (lists up to 5.2) and drf-spectacular 0.30.0 (up to 6.0) don't officially list it; a smoke test passed and tests cover the auth flows.
- JWT: access 15 min, refresh 7 days, rotation + simplejwt `token_blacklist` (logout invalidates the refresh token). URLs: `/api/v1/auth/register/`, `login/`, `refresh/`, `logout/`, `me/`. Rate limits per IP: login 5/min, sign-up 5/hour (DRF scoped throttles, in-memory cache).
- User management: `/api/v1/users/` (admin only, superusers hidden) with `?status=pending|active|banned` and `approve`/`reject`/`ban`/`unban` actions. The rules live in `accounts/services.py` and are shared with Django admin actions; `is_active`/`approved_at` are read-only in the admin panel.
- Phase 2 (links/reviews building blocks) is merged into the recipes phase: shared abstract models live in a `common` app, created when recipes first need them.
- Recipes API design: `POST /recipes/` (form data or JSON) takes title, instructions, cooking method, ingredients, optional `cover_image` file and optional list of links; `PATCH /recipes/{id}` edits the same fields except links (cover upload replaces the old file; empty value removes it). No PUT. Links: `POST /recipes/{id}/links/` adds several at once, `DELETE /recipes/{id}/links/{link_id}/` removes one. Gallery: `POST /recipes/{id}/images/` adds several, `DELETE .../images/{image_id}/` removes one. Cover is its own field, not chosen from the gallery. Deleting a recipe/image or replacing the cover deletes the file from disk. Creating with links and adding links later share one service function.
- Links: any URL is saved; link kind is not stored. YouTube URLs are batch-checked (one API call); a broken YouTube link (no id / video not found) rejects the whole request (nothing saved). YouTube down: saved without info, a daily `refresh_link_metadata` command fills it later. Thumbnail size `high`.
- Recipes: cooking methods `BAKED`, `FRIED`, `BOILED`, `STEWED`, `GRILLED`, `STEAMED`, `RAW`, `OTHER`; an ingredient used in recipes can't be deleted; ingredient name normalization is implemented in the recipes phase (manual ingredient creation uses it).
- Auth: superusers can't be banned via the API; a pending or banned user who logs in with the correct password gets a clear "waiting for approval" / "banned" error; sign-up validates `password2` on the backend; Swagger docs are admin-only; sign-up and login are rate-limited.
- Data model rule: don't store anything that can be derived (e.g. "has pairs" = EXISTS on IngredientPair, link kind = URL host) or that nothing uses.
- Workflow: implement the plan one small step at a time. After each step stop, run checks, propose a one-line commit message and wait for the user's review; move on only when the user says so. Never `git push`.
- Branches: `main` holds only finished, deployable code (hosting and CI/CD planned). After initial setup, work happens on `dev`; features go in their own branches made from `dev` and merge back into `dev`.
- After work is done in worktrees - merge worktree branch locally (`git merge`) into the branch it was made from (`dev` after setup, never straight into `main`); do NOT push worktree branches to remote; Delete worktree after successful merge;
- If needed DTO model - create pydantic schema in separate schemas.py file related to working module
- Never add anything to `__init__.py`. Use full-path imports.
- Domain model, roles and randomizer rules live in `docs/adr.md`; it has priority over `README.md` when they disagree.
- Registration: users sign up with their own password; account stays inactive until an admin approves it.
- Games API: RAWG (not IGDB). Non-favourite training plans are deleted after 30 days (configurable in settings).
- Frontend is plain HTML+CSS+JS, likely in a separate repo; this repo is the REST API backend with JWT.
- Course requirements include tests; write tests for new features (especially randomizers and permissions). Test only our own logic and the config we rely on (no tests of library/framework behaviour), each behaviour once, no redundant tests. Tests go in `<app>/tests/test_*.py` (no `tests.py`), shared fixtures in root `conftest.py`, URLs via `reverse()`. Run with `docker compose run --rm web pytest`; CI runs it too. Rate-limit cache is cleared before every test.
- RecipeNLG: official site (recipenlg.cs.put.poznan.pl) is down; download from Kaggle mirror `paultimothymooney/recipenlg` (`RecipeNLG_dataset.csv`, 2.14 GB, 2,231,142 recipes, `NER` column = cleaned ingredient names). Stored locally in `data/`; never commit it; the import management command reads it from a local path. Ingredient names need normalization (lowercase, singular, merge duplicates). Ahn et al. 2011 flavor network dataset was rejected (only 383 ingredients).
- RecipeNLG test run: 2,231,142 recipes, 4,519 ingredient names in at least 100 recipes, ~230k pairs seen together in at least 20 recipes; counting takes ~1.5 min. NER names have near-duplicates (`cilantro` / `fresh cilantro`, `pepper` / `ground black pepper`) that normalization must merge.
- Ingredient pair scores are computed only from RecipeNLG; own recipes are too few to give meaningful scores.
