from rest_framework import serializers

from common.serializers import RatingsMixin, ReviewSerializer
from games.models import Game, GameCategory, Genre, PlayStatus

MAX_RAWG_ID = 2147483647  # the largest value the database column holds


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class GameListSerializer(RatingsMixin, serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)
    statuses = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "id",
            "name",
            "cover_url",
            "release_date",
            "rawg_rating",
            "categories",
            "genres",
            "statuses",
            "ratings",
            "combined_rating",
        ]

    def get_statuses(self, game) -> dict[str, str | None]:
        by_user = {status.user_id: status.status for status in game.statuses.all()}
        return {admin.username: by_user.get(admin.id) for admin in self.admins()}


class GameDetailSerializer(GameListSerializer):
    reviews = ReviewSerializer(many=True, read_only=True)

    class Meta(GameListSerializer.Meta):
        fields = [*GameListSerializer.Meta.fields, "description", "reviews"]


class GameCategoriesSerializer(serializers.Serializer):
    categories = serializers.ListField(
        child=serializers.ChoiceField(choices=GameCategory.choices),
        allow_empty=False,
    )

    @staticmethod
    def validate_categories(value):
        return list(dict.fromkeys(value))


class GameCreateSerializer(GameCategoriesSerializer):
    rawg_id = serializers.IntegerField(min_value=1, max_value=MAX_RAWG_ID)


class GameStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=PlayStatus.choices)


class GameSearchResultSerializer(serializers.Serializer):
    rawg_id = serializers.IntegerField(source="id")
    game_id = serializers.SerializerMethodField()
    name = serializers.CharField()
    cover_url = serializers.SerializerMethodField()
    release_date = serializers.DateField(source="released", allow_null=True)
    rawg_rating = serializers.FloatField(allow_null=True)
    genres = serializers.SerializerMethodField()

    def get_game_id(self, rawg_game) -> int | None:
        """Our game's id if it's already in the backlog; `game_ids` maps RAWG ids to our ids."""
        return self.context["game_ids"].get(rawg_game.id)

    @staticmethod
    def get_cover_url(rawg_game) -> str:
        return rawg_game.background_image or ""  # same as a stored game without a cover

    @staticmethod
    def get_genres(rawg_game) -> list[str]:
        return [genre.name for genre in rawg_game.genres or []]
