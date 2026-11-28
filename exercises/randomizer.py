from exercises.models import Exercise
from exercises.schemas import RandomExercisesQuery


def pick_exercise_ids(query: RandomExercisesQuery) -> list[int]:
    """Random active exercises matching the filters, each at most once; fewer than `count` if too few match."""
    exercises = Exercise.objects.filter(archived_at__isnull=True)
    if query.muscle:
        exercises = exercises.filter(muscle_categories__overlap=query.muscle)
    if query.load:
        exercises = exercises.filter(load_category__in=query.load)
    if query.intensity_min is not None:
        exercises = exercises.filter(intensity__gte=query.intensity_min)
    if query.intensity_max is not None:
        exercises = exercises.filter(intensity__lte=query.intensity_max)
    return list(exercises.order_by("?").values_list("id", flat=True)[: query.count])
