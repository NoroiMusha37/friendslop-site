# exercises

## Purpose

The training domain: exercises, their shared links and reviews, immutable training plans, favourites and the training randomizer (`/api/v1/exercises/`, `/api/v1/plans/`).

## Ownership

- `models.py`: `Exercise`, `ExerciseLink`, `ExerciseExerciseLink`, `ExerciseReview`, `TrainingPlan`, `PlanExercise`, `UserFavouritePlan`, and the `MuscleCategory`, `LoadCategory` and `PlanMode` choices
- `views.py`, `urls.py`, `serializers.py`: exercises (plus links and reviews through the `common` mixins), archive / restore, plans, favourites
- `filters.py`: exercise and plan list filters
- `randomizer.py` + `schemas.py`: picks exercises for `/exercises/random/` and checks its query parameters
- `exceptions.py`: `ExerciseArchived` (409)
- `admin.py`: Django admin pages; nothing can be deleted, plans are view-only

## Local Contracts

- Exercises are never deleted, only archived. An archived exercise is read-only (fields, links, reviews) and hidden from the randomizer; YouTube refresh still updates its links
- `ExerciseLink` is one row per url, shared through `ExerciseExerciseLink`. Detaching removes only the relation
- Plans are immutable and never deleted: editing saves a new plan with `source_plan`. A plan containing an archived exercise can't be copied until it is restored, but can be favourited
- Favourites are personal to each admin and never inherited by a copy
- List filters apply only to `list`, so archived exercises and old plan versions stay reachable by id

## Work Guidance

## Verification

- `docker compose run --rm web pytest exercises`

## Child DOX Index

None.
