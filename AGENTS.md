# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

When the user requests a durable behavior change, record it here or in the relevant child AGENTS.md.

- Before starting any step: analyze the plan for that step, report all inconsistencies, and ask everything that needs the user's decision; write code only after that is resolved, never pick defaults silently. Start the report with a short plain summary of what the step is about
- When analyzing a step, put parts that aren't specific to the current app (ratings, reviews, links, query checks) in `common` from the start, written for any model
- Don't build half a feature now and the rest later; build only what can be done fully in the current step
- Add dependencies and settings only in the step that first uses them; no unused packages or settings
- Data model: don't store anything that can be derived or that nothing uses
- Workflow: one small step at a time. After each step run the checks, propose a one-line commit message and wait for the user's review; commit only after the checks pass and never chain a commit after a check with `;`. Never `git push`
- Containers: after checks, stop only the containers the agent itself started (check `docker compose ps` first); never stop the user's containers without asking
- Branches: `main` holds only finished, deployable code. Work happens on `dev`; features get their own branch from `dev` and merge back into `dev` locally. Small fixes to code already in `dev` are committed on `dev`, then `dev` is merged into the open feature branch. Worktree branches are merged locally into the branch they came from, never pushed, and the worktree is deleted after the merge
- Code style: split calls and literals that don't fit on a short line one item per line with a trailing comma, like the existing code. Comments explain why. Code, identifiers and comments in English
- Explaining code: explain the actual lines, as one code block per function with a short comment on each line; ask before switching formats
- Tests: only our own logic and config we rely on (no library behaviour, no log messages), each behaviour once; randomizers and permissions matter most for the course. After writing tests, break the code on purpose to confirm they catch it

## Project Contracts

- REST API backend with JWT; the frontend (plain HTML/CSS/JS) lives in a separate repo
- Domain model, roles, API behaviour and randomizer rules live in `docs/adr.md` (priority over `README.md`); record new domain/API decisions there. Step planning lives in the plan outside the repo
- Everything runs in Docker (Django + PostgreSQL 18) via Docker Compose, tests included: `docker compose run --rm web pytest`
- Settings are read with `pydantic-settings` (`config/settings.py`, class `Env`); the database connection uses the same `POSTGRES_*` variables as Docker Compose (no `DATABASE_URL`). `YOUTUBE_API_KEY` is required. `TIME_ZONE = "Europe/Kyiv"`
- Django apps live in the repo root and are created (`startapp`) in the phase that first uses them. Never add anything to `__init__.py`; use full-path imports
- URLs are under `/api/v1/`: each prefix is written once in `config/urls.py` (a new app adds one line to `api_v1`); never repeat a path prefix in any `urls.py`, group paths under one `include([...])` per prefix
- List filtering uses `django-filter`; never hand-write filters it covers. DTOs are pydantic schemas in the module's `schemas.py`
- Ruff isn't in CI: run `ruff check .` and `ruff format --check .` in Docker after each step. `migrations/` folders are excluded
- Tests go in `<app>/tests/test_*.py` (no `tests.py`, no `__init__.py`; pytest `importmode = "importlib"`), shared fixtures in root `conftest.py`, URLs via `reverse()`. Rate-limit cache is cleared before every test, uploads go to a temp `MEDIA_ROOT`
- Django 6.1 is kept although simplejwt 5.5.1 and drf-spectacular 0.30.0 don't officially list it; tests cover the auth flows
- `make` isn't installed on the user's Windows machine: docs show the plain `docker compose` command next to each `Makefile` shortcut, and the agent runs `docker compose` directly

## Child DOX Index

- `accounts/AGENTS.md`: users, roles and statuses, auth, user management, permission classes
- `common/AGENTS.md`: code shared by recipes, games and exercises (links + YouTube, reviews, ratings)
- `recipes/AGENTS.md`: recipes, ingredients and their APIs

Owned by the root:

- `config/`: settings and URLs; also serves the admin-only API docs at `/api/docs/` (schema at `/api/schema/`)
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`: `web` = Django, `db` = PostgreSQL 18
- `Makefile`: dev shortcuts over Docker Compose (`make` lists them); `db-reset` deletes the database volume
- `.env.example`: settings template; the real `.env` is git-ignored
- `.github/workflows/ci.yml`: CI on push/PR to `dev` and `main`, runs migrations check and pytest in the Docker image
- `conftest.py`: shared pytest fixtures (users in each status, API clients, the fake YouTube `youtube`)
- `media/` (git-ignored): uploaded files, served by Django only when `DEBUG` is on
- `docs/adr.md`: domain and API decisions; `README.md`: project description and how to run it
- `CLAUDE.md`: loads this file for Claude Code; holds nothing else
