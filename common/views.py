from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.links import save_links
from common.serializers import AddLinksSerializer, LinkSerializer, ReviewSerializer


class LinksMixin:
    """Adds `POST .../{id}/links/` (several at once) and `DELETE .../{id}/links/{link_id}/` to a viewset
    whose objects have `links`. Permissions come from the viewset."""

    @extend_schema(
        request=AddLinksSerializer,
        responses={201: LinkSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="links",
    )
    def add_links(self, request, pk=None):
        owner = self.get_object()
        serializer = AddLinksSerializer(data=request.data, context={"owner": owner})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            links = save_links(owner, serializer.validated_data["links"])
        return Response(
            LinkSerializer(links, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=None, responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"links/(?P<link_id>\d+)",
    )
    def delete_link(self, request, pk=None, link_id=None):
        get_object_or_404(self.get_object().links, pk=link_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewsMixin:
    """Adds `POST`, `PATCH` and `DELETE .../{id}/review/` to a viewset whose objects have `reviews`. Each request
    acts on the logged-in admin's own review, so nobody can touch another admin's. Permissions come from the viewset."""

    @extend_schema(
        request=ReviewSerializer,
        responses={201: ReviewSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="review",
    )
    def review(self, request, pk=None):
        owner = self.get_object()
        if owner.reviews.filter(author=request.user).exists():
            return Response(
                {"detail": "You have already reviewed this. Use PATCH to change your review."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = owner.reviews.create(author=request.user, **serializer.validated_data)
        return Response(
            ReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=ReviewSerializer,
        responses=ReviewSerializer,
    )
    @review.mapping.patch
    def update_review(self, request, pk=None):
        review = get_object_or_404(self.get_object().reviews, author=request.user)
        serializer = ReviewSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(review, field, value)
        review.save()
        return Response(ReviewSerializer(review).data)

    @extend_schema(request=None, responses={204: None})
    @review.mapping.delete
    def delete_review(self, request, pk=None):
        get_object_or_404(self.get_object().reviews, author=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
