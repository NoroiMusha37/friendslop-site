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
- Django apps live in the repo root (next to `config/`); each app is created (`startapp`, generated stubs are fine) in the phase that first uses it. API URLs are under `/api/v1/`. pytest uses `importmode = "importlib"` (no `__init__.py` in `tests/` folders).
- Lists filtering uses `django-filter` (added when the first filtered list appears).
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
- Course requirements include tests; write tests for new features (especially randomizers and permissions).
- RecipeNLG: official site (recipenlg.cs.put.poznan.pl) is down; download from Kaggle mirror `paultimothymooney/recipenlg` (`RecipeNLG_dataset.csv`, 2.14 GB, 2,231,142 recipes, `NER` column = cleaned ingredient names). Stored locally in `data/`; never commit it; the import management command reads it from a local path. Ingredient names need normalization (lowercase, singular, merge duplicates). Ahn et al. 2011 flavor network dataset was rejected (only 383 ingredients).
- RecipeNLG test run: 2,231,142 recipes, 4,519 ingredient names in at least 100 recipes, ~230k pairs seen together in at least 20 recipes; counting takes ~1.5 min. NER names have near-duplicates (`cilantro` / `fresh cilantro`, `pepper` / `ground black pepper`) that normalization must merge.
- Ingredient pair scores are computed only from RecipeNLG; own recipes are too few to give meaningful scores.
