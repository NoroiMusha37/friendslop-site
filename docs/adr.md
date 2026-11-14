## Roles

- ADMIN: both team members, full access to everything
- USER: can view everything and leave comments on recipes

## Common

- rating: integer 0-10, personal for each admin
- review: admin's text, personal for each admin
- links (youtube, reels, threads, tiktok): only YouTube links get metadata from YouTube API (title, duration,
  thumbnail), others are stored as plain links

## Recipes

- instructions (full recipe text, including ingredient amounts)
- cooking_method (BAKED, FRIED, etc.)
- links
- ingredients (no amounts, those are in instructions)
- image
- rating
- review
- comments (from users)

## Ingredients

- name
- filled once from RecipeNLG by a management command; admins can add missing ones by hand

### Ingredient Pairs

- ingredient_a, ingredient_b
- score (PMI, see Randomizers)

## Games

- RAWG / IGDB API (cover, description, genre, release date, API rating)
- category: SOLO, COOP, MULTIPLAYER
- status: PLANNED, DROPPED, PLAYING, COMPLETED. Personal for each admin, for every category (coop games are often
  played solo)
- rating
- review

## Training

### Exercises

- text description
- links
- muscle_category
- load_category (ENUM): weight load
- intensity: general complexity
- review

### Training Plan

- exercises
- is_favourite: shared for both admins. Plans that are not favourite get deleted automatically after some time
- workout sessions are not stored

## Randomizers

- food randomizer. 2 modes:
    - NAIVE picks random ingredients
    - SMART builds a coherent combination using ingredient pair scores:
        - scores come from how often 2 ingredients appear together in RecipeNLG recipes (~2.2M) compared to chance:
          `PMI = log(recipes with both / expected by chance)`, where expected = recipes with A * recipes with B /
          all recipes
        - pairs seen together in fewer than ~20 recipes are ignored
        - the next ingredient must not have a negative score with any chosen ingredient; it is picked randomly,
          weighted by its average score with chosen ones; too low scores are dropped
        - ingredients without scores are never picked by SMART
- games randomizer. Random game based on GENRE and STATUS
- training plan randomizer. Build plan based on MUSCLE_CATEGORY, LOAD_CATEGORY, INTENSITY
