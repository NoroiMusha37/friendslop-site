from exercises.models import Exercise, PlanExercise, PlanMode, TrainingPlan


def make_exercise(name="Push-up", **fields):
    defaults = {
        "description": "Push the floor away.",
        "muscle_categories": ["CHEST"],
        "load_category": "BODYWEIGHT",
        "intensity": 2,
    }
    return Exercise.objects.create(name=name, **{**defaults, **fields})


def make_plan(*exercises, mode=PlanMode.MANUAL, **fields):
    plan = TrainingPlan.objects.create(name=fields.pop("name", "Monday"), mode=mode, **fields)
    for order, exercise in enumerate(exercises):
        PlanExercise.objects.create(plan=plan, exercise=exercise, order=order)
    return plan
