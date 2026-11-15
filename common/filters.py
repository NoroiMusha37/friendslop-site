import django_filters

from common.ratings import order_by_rating


class RatingOrderingFilter(django_filters.CharFilter):
    """`?ordering=` by combined rating or one admin's rating. The queryset must come from `with_combined_rating`."""

    def __init__(self, **kwargs):
        kwargs.setdefault(
            "help_text", "`combined_rating` or `rating:<admin username>`; prefix with `-` for highest first"
        )
        super().__init__(**kwargs)

    def filter(self, qs, value):
        return order_by_rating(qs, value) if value else qs
