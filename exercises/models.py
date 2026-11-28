from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.functions import Lower

from common.models import BaseLink, BaseReview

MIN_INTENSITY = 1
MAX_INTENSITY = 5


class MuscleCategory(models.TextChoices):
    CHEST = "CHEST"
    BACK = "BACK"
    SHOULDERS = "SHOULDERS"
    ARMS = "ARMS"
    CORE = "CORE"
    LEGS = "LEGS"


class LoadCategory(models.TextChoices):
    BODYWEIGHT = "BODYWEIGHT"
    LIGHT = "LIGHT"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"


class PlanMode(models.TextChoices):
    RANDOM = "RANDOM"
    RANDOM_EDIT = "RANDOM_EDIT"
    MANUAL = "MANUAL"


class ExerciseLink(BaseLink):
    """One row per url, shared by every exercise using it, so its YouTube info is fetched once."""

    url = models.URLField(max_length=500, unique=True)


class Exercise(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    muscle_categories = ArrayField(models.CharField(max_length=20, choices=MuscleCategory))
    load_category = models.CharField(max_length=20, choices=LoadCategory)
    intensity = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(MIN_INTENSITY),
            MaxValueValidator(MAX_INTENSITY),
        ],
    )
    archived_at = models.DateTimeField(null=True, blank=True)
    links = models.ManyToManyField(
        ExerciseLink,
        through="ExerciseExerciseLink",
        related_name="exercises",
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_exercise_name_ci",
            ),
            models.CheckConstraint(
                condition=models.Q(muscle_categories__len__gt=0),
                name="exercise_has_muscle_category",
            ),
            models.CheckConstraint(
                condition=models.Q(intensity__gte=MIN_INTENSITY, intensity__lte=MAX_INTENSITY),
                name="exercise_intensity_range",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None


class ExerciseExerciseLink(models.Model):
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="+",
    )
    link = models.ForeignKey(
        ExerciseLink,
        on_delete=models.CASCADE,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["exercise", "link"],
                name="unique_exercise_link",
            ),
        ]

    def __str__(self):
        return f"{self.exercise}: {self.link}"


class ExerciseReview(BaseReview):
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    class Meta(BaseReview.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["exercise", "author"],
                name="unique_exercise_review_author",
            ),
        ]


class TrainingPlan(models.Model):
    """Immutable: editing a plan saves a new one pointing to it through `source_plan`."""

    name = models.CharField(max_length=200)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # PROTECT: stored plans are kept for analysis, so a plan's history can't lose a step
    source_plan = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="copies",
    )
    mode = models.CharField(max_length=20, choices=PlanMode)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PlanExercise(models.Model):
    plan = models.ForeignKey(
        TrainingPlan,
        on_delete=models.CASCADE,
        related_name="items",
    )
    # PROTECT: stored plans must stay complete
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.PROTECT,
        related_name="+",
    )
    order = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "order"],
                name="unique_plan_exercise_order",
            ),
        ]

    def __str__(self):
        return f"{self.plan} #{self.order}: {self.exercise}"


class UserFavouritePlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    plan = models.ForeignKey(
        TrainingPlan,
        on_delete=models.CASCADE,
        related_name="favourites",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "plan"],
                name="unique_user_favourite_plan",
            ),
        ]

    def __str__(self):
        return f"{self.user}: {self.plan}"
