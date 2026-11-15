# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Facts
Every time you get new information about this project, or new way of interaction with 
library/models/services, or specific instructions from user on how to test/implement new feature,
add short description of acquired knowledge here in bulleted list:
- Domain model, roles, API behaviour and randomizer rules live in `docs/adr.md`; it has priority over `README.md` when they disagree. Record new domain/API decisions there, not here. Step planning lives in the plan, not here.
- Before starting any step: analyze the plan for that step first, report all inconsistencies, and ask EVERYTHING that needs clarification or the user's decision. Write code only after all of that is resolved. Never silently pick defaults.
- When analyzing a step, check which parts aren't specific to the current app (e.g. ratings, reviews, links are shared by recipes, games, exercises) and put them in `common` from the start, written to work with any model; never write them app-specific first.
- Don't write half of a feature now and the rest later: build only what can be done fully (or almost fully) in the current step.
- Add dependencies and settings only in the step that first uses them; no unused packages or settings variables.
- Data model rule: don't store anything that can be derived (e.g. "has pairs" = EXISTS on IngredientPair, link kind = URL host) or that nothing uses.
- Workflow: implement the plan one small step at a time. After each step stop, run checks, propose a one-line commit message and wait for the user's review; move on only when the user says so. Commit only after the checks pass. Never `git push`. Run `docker compose down` after checks so no containers stay running.
- Branches: `main` holds only finished, deployable code (hosting and CI/CD planned). After initial setup, work happens on `dev`; features go in their own branches made from `dev` and merge back into `dev`. Small fixes to code already in `dev` are committed directly on `dev` (no branch), then `dev` is merged into the open feature branch.
- After work is done in worktrees - merge worktree branch locally (`git merge`) into the branch it was made from (`dev` after setup, never straight into `main`); do NOT push worktree branches to remote; Delete worktree after successful merge;
- If needed DTO model - create pydantic schema in separate schemas.py file related to working module
- Never add anything to `__init__.py`. Use full-path imports.
- Frontend is plain HTML+CSS+JS, likely in a separate repo; this repo is the REST API backend with JWT.
- Everything runs in Docker (Django + PostgreSQL 18) via Docker Compose, including tests.
- Settings are read with `pydantic-settings`. Database connection is built from the same `POSTGRES_*` variables Docker Compose uses (no `DATABASE_URL`). `YOUTUBE_API_KEY` is required. `TIME_ZONE = "Europe/Kyiv"`.
- Django apps live in the repo root (next to `config/`); each app is created (`startapp`, generated stubs are fine) in the phase that first uses it. API URLs are under `/api/v1/`: each prefix is written once in `config/urls.py`; a new app adds one line to the `api_v1` list. Never repeat a path prefix in any urls.py: group paths under one `include([...])` per prefix (e.g. `auth/` in `accounts/urls.py`).
- Lists filtering uses `django-filter`; never hand-write filters it covers.
- Admin = `is_superuser` (DRF's `IsAdminUser` checks `is_staff`, so use our `accounts.permissions` classes). User status changes go through `accounts/services.py`, shared by the API and the Django admin actions.
- Ruff is not in CI: the agent runs `ruff check .` and `ruff format --check .` (in Docker) after each step, before proposing a commit/merge. Unused imports in `startapp` stubs are left as they are. `migrations/` folders are excluded from ruff.
- Tests: test only our own logic and the config we rely on (no tests of library/framework behaviour), each behaviour once, no redundant tests; course requirements include tests, especially randomizers and permissions. Tests go in `<app>/tests/test_*.py` (no `tests.py`), shared fixtures in root `conftest.py`, URLs via `reverse()`. pytest uses `importmode = "importlib"` (no `__init__.py` in `tests/` folders). Run with `docker compose run --rm web pytest`; CI runs it too. Rate-limit cache is cleared before every test; uploads go to a temp `MEDIA_ROOT`. YouTube is faked with the root `youtube` fixture (`responses`), never called for real. After writing tests, break the code on purpose to confirm they catch it.
- Django 6.1 is kept even though simplejwt 5.5.1 (lists up to 5.2) and drf-spectacular 0.30.0 (up to 6.0) don't officially list it; a smoke test passed and tests cover the auth flows.
- RecipeNLG: official site (recipenlg.cs.put.poznan.pl) is down; download from Kaggle mirror `paultimothymooney/recipenlg` (`RecipeNLG_dataset.csv`, 2.14 GB, 2,231,142 recipes, `NER` column = cleaned ingredient names). Stored locally in `data/`; never commit it; the import management command reads it from a local path. Ahn et al. 2011 flavor network dataset was rejected (only 383 ingredients).
- RecipeNLG test run: 4,519 ingredient names in at least 100 recipes, ~230k pairs seen together in at least 20 recipes; counting takes ~1.5 min. NER names have near-duplicates (`cilantro` / `fresh cilantro`, `pepper` / `ground black pepper`) that the import's cleanup must merge.
