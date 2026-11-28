from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from common.links import prepare_links, save_links, stored_urls
from common.serializers import LinkSerializer, RatingsMixin, ReviewSerializer
from exercises.exceptions import ExerciseArchived
from exercises.models import (
    Exercise,
    ExerciseLink,
    MuscleCategory,
    PlanExercise,
    PlanMode,
    TrainingPlan,
)

MAX_ID = 2147483647  # the largest value the database column holds


class ExerciseListSerializer(RatingsMixin, serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = (
            "id",
            "name",
            "muscle_categories",
            "load_category",
            "intensity",
            "archived_at",
            "ratings",
            "combined_rating",
        )


class ExerciseDetailSerializer(ExerciseListSerializer):
    links = LinkSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta(ExerciseListSerializer.Meta):
        fields = (*ExerciseListSerializer.Meta.fields, "description", "links", "reviews")


class ExerciseWriteSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=200,
        validators=[
            UniqueValidator(
                queryset=Exercise.objects.all(),
                lookup="iexact",
                message="An exercise with this name already exists.",
            ),
        ],
    )
    muscle_categories = serializers.ListField(
        child=serializers.ChoiceField(choices=MuscleCategory.choices),
        allow_empty=False,
    )

    class Meta:
        model = Exercise
        fields = ("name", "description", "muscle_categories", "load_category", "intensity")

    @staticmethod
    def validate_muscle_categories(value):
        return list(dict.fromkeys(value))


class ExerciseCreateSerializer(ExerciseWriteSerializer):
    """Creating also takes an optional list of links; links are added later through `POST .../links/`."""

    links = serializers.ListField(
        child=serializers.URLField(max_length=500),
        required=False,
        write_only=True,
    )

    class Meta(ExerciseWriteSerializer.Meta):
        fields = (*ExerciseWriteSerializer.Meta.fields, "links")

    @staticmethod
    def validate_links(urls):
        # Checked (and YouTube asked) before anything is written
        return prepare_links(urls, stored_urls=stored_urls(ExerciseLink, urls))

    def create(self, validated_data):
        links = validated_data.pop("links", [])
        with transaction.atomic():
            exercise = Exercise.objects.create(**validated_data)
            save_links(exercise, links)
        return exercise


class PlanExerciseSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="exercise_id")
    name = serializers.CharField(source="exercise.name")
    muscle_categories = serializers.ListField(
        source="exercise.muscle_categories",
        child=serializers.CharField(),
    )
    load_category = serializers.CharField(source="exercise.load_category")
    intensity = serializers.IntegerField(source="exercise.intensity")
    is_archived = serializers.BooleanField(source="exercise.is_archived")


class TrainingPlanSerializer(serializers.ModelSerializer):
    user = serializers.CharField(
        source="user.username",
        allow_null=True,
        default=None,
    )
    exercises = PlanExerciseSerializer(source="items", many=True)
    is_favourite = serializers.BooleanField()

    class Meta:
        model = TrainingPlan
        fields = (
            "id",
            "name",
            "user",
            "source_plan",
            "mode",
            "created_at",
            "is_favourite",
            "exercises",
        )


class TrainingPlanCreateSerializer(serializers.Serializer):
    """Saving always creates a new plan; `source_plan` says which one was edited, if any."""

    name = serializers.CharField(max_length=200)
    mode = serializers.ChoiceField(choices=PlanMode.choices)
    source_plan = serializers.PrimaryKeyRelatedField(
        queryset=TrainingPlan.objects.all(),
        required=False,
        allow_null=True,
    )
    # Plain ids, because the same exercise may appear several times
    exercises = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=MAX_ID),
        allow_empty=False,
    )

    @staticmethod
    def validate_exercises(ids):
        found = Exercise.objects.in_bulk(ids)
        if unknown := sorted(set(ids) - found.keys()):
            raise serializers.ValidationError(f"Unknown exercise ids: {unknown}.")
        return [found[exercise_id] for exercise_id in ids]

    def validate(self, attrs):
        source = attrs.get("source_plan")
        if source:
            required = PlanMode.MANUAL if source.mode == PlanMode.MANUAL else PlanMode.RANDOM_EDIT
            if attrs["mode"] != required:
                raise serializers.ValidationError({"mode": [f"A copy of this plan must use {required}."]})
            # Checked on the source too: a plan with an archived exercise can't be edited until it is restored
            if source.items.filter(exercise__archived_at__isnull=False).exists():
                raise ExerciseArchived
        if any(exercise.is_archived for exercise in attrs["exercises"]):
            raise ExerciseArchived
        return attrs

    def create(self, validated_data):
        exercises = validated_data.pop("exercises")
        with transaction.atomic():
            plan = TrainingPlan.objects.create(**validated_data)
            PlanExercise.objects.bulk_create(
                [
                    PlanExercise(
                        plan=plan,
                        exercise=exercise,
                        order=order,
                    )
                    for order, exercise in enumerate(exercises)
                ]
            )
        return plan
