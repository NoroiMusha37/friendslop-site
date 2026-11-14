# CLAUDE.md

This file provides guidance to agents when working with code in this repository.

## Facts
Every time you get new information about this project, or new way of interaction with 
library/models/services, or specific instructions from user on how to test/implement new feature,
add short description of acquired knowledge here in bulleted list:
- Branches: `main` holds only finished, deployable code (hosting and CI/CD planned). After initial setup, work happens on `dev`; features go in their own branches made from `dev` and merge back into `dev`.
- After work is done in worktrees - merge worktree branch locally (`git merge`) into the branch it was made from (`dev` after setup, never straight into `main`); do NOT push worktree branches to remote; Delete worktree after successful merge;
- If needed DTO model - create pydantic schema in separate schemas.py file related to working module
- Never add anything to `__init__.py`. Use full-path imports.
- Domain model, roles and randomizer rules live in `docs/adr.md`; it has priority over `README.md` when they disagree.
- Frontend is plain HTML+CSS+JS, likely in a separate repo; this repo is the REST API backend with JWT.
- Course requirements include tests; write tests for new features (especially randomizers and permissions).
- RecipeNLG: official site (recipenlg.cs.put.poznan.pl) is down; download from Kaggle mirror `paultimothymooney/recipenlg` (`RecipeNLG_dataset.csv`, 2.14 GB, 2,231,142 recipes, `NER` column = cleaned ingredient names). Stored locally in `data/`; never commit it; the import management command reads it from a local path. Ingredient names need normalization (lowercase, singular, merge duplicates). Ahn et al. 2011 flavor network dataset was rejected (only 383 ingredients).
- RecipeNLG test run: 2,231,142 recipes, 4,519 ingredient names in at least 100 recipes, ~230k pairs seen together in at least 20 recipes; counting takes ~1.5 min. NER names have near-duplicates (`cilantro` / `fresh cilantro`, `pepper` / `ground black pepper`) that normalization must merge.
- Ingredient pair scores are computed only from RecipeNLG; own recipes are too few to give meaningful scores.
