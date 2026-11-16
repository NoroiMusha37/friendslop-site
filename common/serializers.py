from rest_framework import serializers

from accounts.models import User
from common.links import prepare_links


class BaseReviewSerializer(serializers.ModelSerializer):
    """Subclasses set `Meta.model` to a `BaseReview` subclass."""

    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        fields = ("id", "author", "rating", "text")


class LinkSerializer(serializers.Serializer):
    """Any app's link (all of them share the `BaseLink` fields), so no per-app subclass is needed."""

    id = serializers.IntegerField(read_only=True)
    url = serializers.URLField(read_only=True)
    title = serializers.CharField(read_only=True)
    duration = serializers.DurationField(read_only=True)
    thumbnail_url = serializers.URLField(read_only=True)


class AddLinksSerializer(serializers.Serializer):
    """Body of `POST .../links/`. The object the links are added to is passed in the context as `owner`."""

    links = serializers.ListField(
        child=serializers.URLField(max_length=500),
        allow_empty=False,
    )

    def validate_links(self, urls):
        existing = set(self.context["owner"].links.values_list("url", flat=True))
        return prepare_links(urls, existing)


class RatingsMixin(serializers.Serializer):
    """Every admin's rating by username (null if not rated) and the combined rating.

    The object needs prefetched `reviews` and the `combined_rating` annotation (see `common.ratings`).
    """

    ratings = serializers.SerializerMethodField()
    combined_rating = serializers.SerializerMethodField()

    def get_ratings(self, obj) -> dict[str, int | None]:
        # The context is shared by every item of a list, so admins are loaded once per request
        if "admins" not in self.context:
            self.context["admins"] = list(
                User.objects.filter(is_superuser=True).order_by("id"),
            )
        by_author = {review.author_id: review.rating for review in obj.reviews.all()}
        return {admin.username: by_author.get(admin.id) for admin in self.context["admins"]}

    @staticmethod
    def get_combined_rating(obj) -> float | None:
        return None if obj.combined_rating is None else round(obj.combined_rating, 1)
