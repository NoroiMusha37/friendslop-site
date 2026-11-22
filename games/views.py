from django.db import IntegrityError
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsAdminOrReadOnly
from common.query import parse_query
from common.ratings import with_combined_rating
from common.views import ReviewsMixin
from games.filters import GameFilter
from games.models import Game, GameStatus, Genre
from games.rawg import get_game, search_games
from games.schemas import GameSearchQuery
from games.serializers import (
    GameCategoriesSerializer,
    GameCreateSerializer,
    GameDetailSerializer,
    GameListSerializer,
    GameSearchResultSerializer,
    GameStatusSerializer,
    GenreSerializer,
)
from games.services import create_game


def already_added(rawg_id: int) -> Response:
    return Response(
        {
            "detail": "This game is already added.",
            "game_id": Game.objects.get(rawg_id=rawg_id).pk,
        },
        status=status.HTTP_409_CONFLICT,
    )


class GameViewSet(
    ReviewsMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = GameFilter

    def get_queryset(self):
        return with_combined_rating(
            Game.objects.prefetch_related("genres", "statuses", "reviews__author"),
        )

    def get_serializer_class(self):
        return GameListSerializer if self.action == "list" else GameDetailSerializer

    def get_permissions(self):
        if self.action == "search":
            return [IsAdmin()]
        return super().get_permissions()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if self.action == "list" and not self.request.query_params.get("ordering"):
            return queryset.order_by("-id")
        return queryset

    @extend_schema(
        request=GameCreateSerializer,
        responses={
            201: GameDetailSerializer,
            409: inline_serializer(
                "GameAlreadyAdded",
                {
                    "detail": serializers.CharField(),
                    "game_id": serializers.IntegerField(),
                },
            ),
        },
    )
    def create(self, request):
        serializer = GameCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rawg_id = serializer.validated_data["rawg_id"]
        if Game.objects.filter(rawg_id=rawg_id).exists():
            return already_added(rawg_id)

        rawg_game = get_game(rawg_id)
        if rawg_game is None:
            raise serializers.ValidationError({"rawg_id": ["RAWG has no game with this id."]})
        try:
            game = create_game(rawg_game, serializer.validated_data["categories"])
        except IntegrityError:
            # A double-click: the other request saved the game after the check above
            return already_added(rawg_id)
        game = self.get_queryset().get(pk=game.pk)  # adds the ratings the reply shows
        return Response(self.get_serializer(game).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=GameCategoriesSerializer,
        responses=GameDetailSerializer,
    )
    def partial_update(self, request, pk=None):
        game = self.get_object()
        serializer = GameCategoriesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game.categories = serializer.validated_data["categories"]
        game.save(update_fields=["categories"])
        return Response(self.get_serializer(game).data)

    @extend_schema(responses=GenreSerializer(many=True))
    @action(
        detail=False,
        methods=["get"],
        url_path="genres",
        url_name="genres",
        filterset_class=None,
    )
    def genres(self, request):
        genres = Genre.objects.filter(games__isnull=False).distinct().order_by("name")
        return Response(GenreSerializer(genres, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("q", str, required=True, description="game name, at least 2 characters")],
        responses=GameSearchResultSerializer(many=True),
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="search",
        url_name="search",
    )
    def search(self, request):
        query = parse_query(GameSearchQuery, request)
        results = search_games(query.q)
        game_ids = dict(
            Game.objects.filter(rawg_id__in=[game.id for game in results]).values_list("rawg_id", "id"),
        )
        return Response(
            GameSearchResultSerializer(
                results,
                many=True,
                context={"game_ids": game_ids},
            ).data,
        )

    @extend_schema(
        request=GameStatusSerializer,
        responses=GameStatusSerializer,
    )
    @action(
        detail=True,
        methods=["put"],
        url_path="status",
        url_name="status",
    )
    def set_status(self, request, pk=None):
        game = self.get_object()
        serializer = GameStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        GameStatus.objects.update_or_create(
            game=game,
            user=request.user,
            defaults=serializer.validated_data,
        )
        return Response(serializer.data)

    @extend_schema(request=None, responses={204: None})
    @set_status.mapping.delete
    def clear_status(self, request, pk=None):
        GameStatus.objects.filter(game=self.get_object(), user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
