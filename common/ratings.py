"""Rating helpers for any model whose reviews (a `BaseReview` subclass) are reachable as `reviews`."""

from django.db.models import Avg, F, OuterRef, Subquery
from rest_framework.exceptions import ValidationError

from accounts.models import User


def with_combined_rating(queryset):
    return queryset.annotate(combined_rating=Avg("reviews__rating"))


def order_by_rating(queryset, value):
    """`value` is `combined_rating` or `rating:<admin username>`, with `-` for highest first. Unrated go last."""
    descending = value.startswith("-")
    key = value.removeprefix("-")
    if key == "combined_rating":
        rating = F("combined_rating")
    elif key.startswith("rating:"):
        username = key.removeprefix("rating:")
        if not User.objects.filter(username=username, is_superuser=True).exists():
            raise ValidationError({"ordering": f"No admin named '{username}'."})
        reviews = queryset.model._meta.get_field("reviews")
        rating = Subquery(
            reviews.related_model.objects.filter(
                **{reviews.field.name: OuterRef("pk")}, author__username=username
            ).values("rating")[:1]
        )
    else:
        raise ValidationError(
            {"ordering": "Use `combined_rating` or `rating:<admin username>`."},
        )
    rating = rating.desc(nulls_last=True) if descending else rating.asc(nulls_last=True)
    return queryset.order_by(rating, "-id")
