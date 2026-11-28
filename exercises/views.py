from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsAdminOrReadOnly
from common.query import parse_query
from common.ratings import with_combined_rating
from common.views import LinksMixin, ReviewsMixin
from exercises.exceptions import ExerciseArchived
from exercises.filters import ExerciseFilter, TrainingPlanFilter
from exercises.models import Exercise, PlanExercise, TrainingPlan, UserFavouritePlan
from exercises.randomizer import pick_exercise_ids
from exercises.schemas import RandomExercisesQuery
from exercises.serializers import (
    ExerciseCreateSerializer,
    ExerciseDetailSerializer,
    ExerciseListSerializer,
    ExerciseWriteSerializer,
    TrainingPlanCreateSerializer,
    TrainingPlanSerializer,
)


# Create and edit take the write fields but answer with the full exercise; this tells the API docs
@extend_schema_view(
    create=extend_schema(responses={201: ExerciseDetailSerializer}),
    partial_update=extend_schema(responses=ExerciseDetailSerializer),
)
class ExerciseViewSet(
    LinksMixin,
    ReviewsMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Exercises are archived instead of deleted; `delete` stays allowed for the link and review routes."""

    permission_classes = [IsAdminOrReadOnly]
    filterset_class = ExerciseFilter
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = with_combined_rating(
            Exercise.objects.prefetch_related("reviews__author"),
        ).order_by("-id")
        if self.action == "list":
            return queryset
        return queryset.prefetch_related("links")

    def get_permissions(self):
        if self.action == "random_exercises":
            return [IsAdmin()]
        return super().get_permissions()

    def filter_queryset(self, queryset):
        # Only the list filters: an archived exercise must stay reachable by id
        if self.action != "list":
            return queryset
        return super().filter_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return ExerciseListSerializer
        if self.action == "create":
            return ExerciseCreateSerializer
        if self.action == "partial_update":
            return ExerciseWriteSerializer
        return ExerciseDetailSerializer

    def check_owner_writable(self, owner) -> None:
        if owner.is_archived:
            raise ExerciseArchived

    def _detail_response(self, exercise_id, status_code=status.HTTP_200_OK):
        exercise = self.get_queryset().get(pk=exercise_id)
        return Response(
            ExerciseDetailSerializer(exercise, context=self.get_serializer_context()).data,
            status=status_code,
        )

    @staticmethod
    def _save(serializer):
        try:
            with transaction.atomic():
                return serializer.save()
        except IntegrityError as e:  # two admins saving one name at once get past the serializer's check
            raise serializers.ValidationError({"name": ["An exercise with this name already exists."]}) from e

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._detail_response(self._save(serializer).pk, status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        exercise = self.get_object()
        self.check_owner_writable(exercise)
        serializer = self.get_serializer(
            exercise,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return self._detail_response(self._save(serializer).pk)

    @extend_schema(request=None, responses=ExerciseDetailSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path="archive",
    )
    def archive(self, request, pk=None):
        exercise = self.get_object()
        # Conditional update, so a double-click can't overwrite the first archive time
        if not Exercise.objects.filter(pk=exercise.pk, archived_at__isnull=True).update(archived_at=timezone.now()):
            return Response(
                {"detail": "This exercise is already archived."},
                status=status.HTTP_409_CONFLICT,
            )
        return self._detail_response(exercise.pk)

    @extend_schema(request=None, responses=ExerciseDetailSerializer)
    @action(
        detail=True,
        methods=["post"],
        url_path="restore",
    )
    def restore(self, request, pk=None):
        exercise = self.get_object()
        if not Exercise.objects.filter(pk=exercise.pk, archived_at__isnull=False).update(archived_at=None):
            return Response(
                {"detail": "This exercise is not archived."},
                status=status.HTTP_409_CONFLICT,
            )
        return self._detail_response(exercise.pk)

    @extend_schema(
        parameters=[
            OpenApiParameter("count", int, description="1-20, default 5"),
            OpenApiParameter("muscle", str, description="muscle categories, any of them matches, e.g. `CHEST,BACK`"),
            OpenApiParameter("load", str, description="load categories, any of them matches, e.g. `LIGHT,MEDIUM`"),
            OpenApiParameter("intensity_min", int, description="1-5"),
            OpenApiParameter("intensity_max", int, description="1-5"),
        ],
        responses=inline_serializer("RandomExercises", {"exercises": ExerciseListSerializer(many=True)}),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="random",
        url_name="random",
    )
    def random_exercises(self, request):
        ids = pick_exercise_ids(parse_query(RandomExercisesQuery, request))
        by_id = self.get_queryset().in_bulk(ids)
        data = ExerciseListSerializer(
            [by_id[exercise_id] for exercise_id in ids],
            many=True,
            context=self.get_serializer_context(),
        ).data
        return Response({"exercises": data})


@extend_schema_view(
    create=extend_schema(responses={201: TrainingPlanSerializer}),
)
class TrainingPlanViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Plans are immutable and never deleted: editing one means creating a new plan with `source_plan` set."""

    permission_classes = [IsAdminOrReadOnly]
    filterset_class = TrainingPlanFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # the API docs build this without a logged-in user
            return TrainingPlan.objects.none()
        favourites = UserFavouritePlan.objects.filter(
            user=self.request.user,
            plan=OuterRef("pk"),
        )
        return (
            TrainingPlan.objects.select_related("user")
            .prefetch_related(Prefetch("items", PlanExercise.objects.select_related("exercise")))
            .annotate(is_favourite=Exists(favourites))
            .order_by("-id")
        )

    def filter_queryset(self, queryset):
        # Only the list filters: older versions must stay reachable by id
        if self.action != "list":
            return queryset
        return super().filter_queryset(queryset)

    def get_serializer_class(self):
        if self.action == "create":
            return TrainingPlanCreateSerializer
        return TrainingPlanSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.save(user=request.user)
        return Response(
            TrainingPlanSerializer(self.get_queryset().get(pk=plan.pk)).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={204: None})
    @action(
        detail=True,
        methods=["put"],
        url_path="favourite",
    )
    def favourite(self, request, pk=None):
        UserFavouritePlan.objects.get_or_create(user=request.user, plan=self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses={204: None})
    @favourite.mapping.delete
    def unfavourite(self, request, pk=None):
        UserFavouritePlan.objects.filter(user=request.user, plan=self.get_object()).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
