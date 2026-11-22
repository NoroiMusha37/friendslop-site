import django_filters

from common.ratings import order_by_rating


class RatingOrderingFilter(django_filters.CharFilter):
    """`?ordering=` by a rating field or one admin's rating. The queryset must come from `with_combined_rating`."""

    def __init__(self, rating_fields=("combined_rating",), **kwargs):
        self.rating_fields = rating_fields
        names = ", ".join(f"`{field}`" for field in rating_fields)
        kwargs.setdefault("help_text", f"{names} or `rating:<admin username>`; prefix with `-` for highest first")
        super().__init__(**kwargs)

    def filter(self, qs, value):
        return order_by_rating(qs, value, self.rating_fields) if value else qs
