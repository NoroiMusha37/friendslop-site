from rest_framework import serializers

from accounts.models import User


class BaseReviewSerializer(serializers.ModelSerializer):
    """Subclasses set `Meta.model` to a `BaseReview` subclass."""

    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        fields = ("id", "author", "rating", "text")


class BaseLinkSerializer(serializers.ModelSerializer):
    """Subclasses set `Meta.model` to a `BaseLink` subclass."""

    class Meta:
        fields = ("id", "url", "title", "duration", "thumbnail_url")


class RatingsMixin(serializers.Serializer):
    """Every admin's rating by username (null if not rated) and the combined rating.

    The object needs prefetched `reviews` and the `combined_rating` annotation (see `common.ratings`).
    """

    ratings = serializers.SerializerMethodField()
    combined_rating = serializers.SerializerMethodField()

    def get_ratings(self, obj) -> dict[str, int | None]:
        # The context is shared by every item of a list, so admins are loaded once per request
        if "admins" not in self.context:
            self.context["admins"] = list(User.objects.filter(is_superuser=True).order_by("id"))
        by_author = {review.author_id: review.rating for review in obj.reviews.all()}
        return {admin.username: by_author.get(admin.id) for admin in self.context["admins"]}

    @staticmethod
    def get_combined_rating(obj) -> float | None:
        return None if obj.combined_rating is None else round(obj.combined_rating, 1)
