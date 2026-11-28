from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from common.links import fill_missing_info, link_models, link_owners, remove_link, save_links
from common.serializers import AddLinksSerializer, LinkSerializer, ReviewSerializer


class WritableOwnerMixin:
    """Lets a viewset refuse link and review changes on some objects by raising from `check_owner_writable`."""

    def check_owner_writable(self, owner) -> None:
        pass


class LinksMixin(WritableOwnerMixin):
    """Adds `POST .../{id}/links/` (several at once), `POST .../{id}/links/refresh/` and
    `DELETE .../{id}/links/{link_id}/` to a viewset whose objects have `links`. Permissions come from the viewset."""

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
        self.check_owner_writable(owner)
        serializer = AddLinksSerializer(data=request.data, context={"owner": owner})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            links = save_links(owner, serializer.validated_data["links"])
        return Response(
            LinkSerializer(links, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=None,
        responses=inline_serializer(
            "RefreshObjectLinksResult",
            {
                "links": LinkSerializer(many=True),
                "not_found": serializers.ListField(child=serializers.IntegerField()),
            },
        ),
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="links/refresh",
    )
    def refresh_links(self, request, pk=None):
        """Fills in missing YouTube info of this object's links; returns all its links and the ids of the links
        whose video is gone."""
        links = list(self.get_object().links.order_by("id"))
        _, not_found = fill_missing_info(links)
        return Response(
            {
                "links": LinkSerializer(links, many=True).data,
                "not_found": [link.id for link in not_found],
            },
        )

    @extend_schema(request=None, responses={204: None})
    @action(
        detail=True,
        methods=["delete"],
        url_path=r"links/(?P<link_id>\d+)",
    )
    def delete_link(self, request, pk=None, link_id=None):
        owner = self.get_object()
        self.check_owner_writable(owner)
        remove_link(owner, get_object_or_404(owner.links, pk=link_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReviewsMixin(WritableOwnerMixin):
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
        self.check_owner_writable(owner)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                review = owner.reviews.create(author=request.user, **serializer.validated_data)
        except IntegrityError:  # the database allows one review per author, which also covers a double-click
            return Response(
                {"detail": "You have already reviewed this. Use PATCH to change your review."},
                status=status.HTTP_409_CONFLICT,
            )
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
        owner = self.get_object()
        self.check_owner_writable(owner)
        review = get_object_or_404(owner.reviews, author=request.user)
        serializer = ReviewSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(review, field, value)
        review.save()
        return Response(ReviewSerializer(review).data)

    @extend_schema(request=None, responses={204: None})
    @review.mapping.delete
    def delete_review(self, request, pk=None):
        owner = self.get_object()
        self.check_owner_writable(owner)
        get_object_or_404(owner.reviews, author=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefreshLinksView(APIView):
    """`POST /links/refresh/`: fills in missing YouTube info of every link (recipes, exercises, ...)."""

    permission_classes = [IsAdmin]

    @extend_schema(
        request=None,
        responses=inline_serializer(
            "RefreshLinksResult",
            {
                "filled": serializers.IntegerField(),
                "not_found": inline_serializer(
                    "GoneVideoLink",
                    {
                        "url": serializers.URLField(),
                        "type": serializers.CharField(),
                        "object_id": serializers.IntegerField(),
                    },
                    many=True,
                ),
            },
        ),
    )
    def post(self, request):
        links = [link for model in link_models() for link in model.objects.filter(title="")]
        filled, not_found = fill_missing_info(links)
        return Response({"filled": filled, "not_found": [entry for link in not_found for entry in gone_link(link)]})


def gone_link(link) -> list[dict]:
    """One entry per object using a link with a removed video, so the frontend can point the admin to each page."""
    return [
        {
            "url": link.url,
            "type": owner_type,
            "object_id": object_id,
        }
        for owner_type, object_id in link_owners(link)
    ]
