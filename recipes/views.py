from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsAdminOrReadOnly
from common.ratings import with_combined_rating
from common.views import LinksMixin
from recipes.filters import RecipeFilter
from recipes.models import Recipe, RecipeImage
from recipes.serializers import (
    AddImagesSerializer,
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
class RecipeViewSet(LinksMixin, viewsets.ModelViewSet):
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
