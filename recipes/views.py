from django.db import transaction
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsAdminOrReadOnly, IsAuthorOrAdmin, IsRegularUser
from common.ratings import with_combined_rating
from common.views import LinksMixin, ReviewsMixin
from recipes.filters import IngredientFilter, RecipeFilter
from recipes.models import Ingredient, Recipe, RecipeComment, RecipeImage
from recipes.serializers import (
    AddImagesSerializer,
    IngredientSerializer,
    RecipeCommentSerializer,
    RecipeCreateSerializer,
    RecipeDetailSerializer,
    RecipeImageSerializer,
    RecipeListSerializer,
    RecipeWriteSerializer,
)


# Create and edit take the write fields but answer with the full recipe; this tells the API docs
@extend_schema_view(
    create=extend_schema(responses={201: RecipeDetailSerializer}),
    partial_update=extend_schema(responses=RecipeDetailSerializer),
)
class RecipeViewSet(LinksMixin, ReviewsMixin, viewsets.ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = RecipeFilter
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = with_combined_rating(
            Recipe.objects.prefetch_related("reviews__author"),
        )
        if self.action == "list":
            return queryset
        return queryset.annotate(comment_count=Count("comments", distinct=True)).prefetch_related(
            "ingredients",
            "images",
            "links",
        )

    def get_permissions(self):
        if self.action == "add_comment":
            return [IsRegularUser()]
        if self.action == "delete_comment":
            return [IsAuthorOrAdmin()]
        return super().get_permissions()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action != "list" or "ordering" in self.request.query_params:
            return queryset
        # Default order: search relevance first (if searching), then newest
        if "search" in self.request.query_params:
            return queryset.order_by("search_priority", "-id")
        return queryset.order_by("-id")

    def get_serializer_class(self):
        if self.action == "list":
            return RecipeListSerializer
        if self.action == "create":
            return RecipeCreateSerializer
        if self.action == "partial_update":
            return RecipeWriteSerializer
        return RecipeDetailSerializer

    def _detail_response(self, recipe, status_code):
        recipe = self.get_queryset().get(pk=recipe.pk)
        return Response(
            RecipeDetailSerializer(recipe, context=self.get_serializer_context()).data,
            status=status_code,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._detail_response(serializer.save(), status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(),
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        return self._detail_response(serializer.save(), status.HTTP_200_OK)

    @extend_schema(
        request={"multipart/form-data": AddImagesSerializer},
        responses={201: RecipeImageSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="images",
        parser_classes=[MultiPartParser],
    )
    def add_images(self, request, pk=None):
        recipe = self.get_object()
        serializer = AddImagesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        images = []
        try:
            with transaction.atomic():
                for file in serializer.validated_data["images"]:
                    image = RecipeImage(recipe=recipe, image=file)
                    images.append(image)  # tracked before saving, so a half-saved one is cleaned up too
                    image.save()
        except Exception:
            for image in images:
                image.image.delete(save=False)
            raise
        data = RecipeImageSerializer(
            images,
            many=True,
            context=self.get_serializer_context(),
        ).data
        return Response(data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"images/(?P<image_id>\d+)",
    )
    def delete_image(self, request, pk=None, image_id=None):
        # The file itself is removed by the post_delete handler in recipes/signals.py
        get_object_or_404(self.get_object().images, pk=image_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses=RecipeCommentSerializer(many=True))
    @action(
        detail=True,
        methods=["get"],
        url_path="comments",
    )
    def comments(self, request, pk=None):
        comments = self.get_object().comments.select_related("author")
        return Response(RecipeCommentSerializer(comments, many=True).data)

    @extend_schema(
        request=RecipeCommentSerializer,
        responses={201: RecipeCommentSerializer},
    )
    @comments.mapping.post
    def add_comment(self, request, pk=None):
        serializer = RecipeCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(recipe=self.get_object(), author=request.user)
        return Response(
            RecipeCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"comments/(?P<comment_id>\d+)",
    )
    def delete_comment(self, request, pk=None, comment_id=None):
        comment = get_object_or_404(RecipeComment, pk=comment_id, recipe_id=pk)
        self.check_object_permissions(request, comment)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Search for the recipe form (`?search=`), adding missing ingredients, deleting unused ones."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = IngredientFilter

    def filter_queryset(self, queryset):
        if self.action != "list":
            return queryset
        return super().filter_queryset(queryset)

    def destroy(self, request, *args, **kwargs):
        try:
            self.get_object().delete()
        except ProtectedError as e:
            return Response(
                {"detail": f"This ingredient is used in {len(e.protected_objects)} recipe(s)."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
