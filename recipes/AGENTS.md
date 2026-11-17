# recipes

## Purpose

Recipes and ingredients: the recipes API (`/api/v1/recipes/`) and the ingredients API (`/api/v1/ingredients/`).

## Ownership

- `models.py`: `Ingredient`, `Recipe`, `RecipeIngredient`, `RecipeImage`, `RecipeLink`, `RecipeReview`, `RecipeComment`
- `views.py`, `urls.py`, `serializers.py`: recipe CRUD, gallery images, comments (plus links and reviews through the `common` mixins), ingredient search / add / delete
- `filters.py`: recipe filters, search and rating sort; the ingredient type-ahead search
- `signals.py`: deletes image files from disk when recipes or images go away
- `admin.py`: Django admin pages; comments are view-and-delete only there

## Local Contracts

- Images: at most 5 MB, HEIC refused with a clear message; replaced or deleted images are removed from disk after the transaction commits
- Ingredient names typed by hand get basic cleanup (`clean_ingredient_name`: lowercase, trimmed, single spaces), in the API and the Django admin
- An ingredient used in a recipe can't be deleted (the database protects it; the API answers 409)
- RecipeNLG dataset: `data/RecipeNLG_dataset.csv` (Kaggle mirror `paultimothymooney/recipenlg`, 2.14 GB, 2,231,142 recipes; the official site is down). Stored locally only, never committed

## Work Guidance

## Verification

- `docker compose run --rm web pytest recipes`

## Child DOX Index

None.
