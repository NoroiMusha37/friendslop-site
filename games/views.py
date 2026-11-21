from django.db import IntegrityError
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdmin, IsAdminOrReadOnly
from common.query import parse_query
from games.models import Game
from games.rawg import get_game, search_games
from games.schemas import GameSearchQuery
from games.serializers import GameCreateSerializer, GameSearchResultSerializer, GameSerializer
from games.services import create_game


def already_added(rawg_id: int) -> Response:
    return Response(
        {
            "detail": "This game is already added.",
            "game_id": Game.objects.get(rawg_id=rawg_id).pk,
        },
        status=status.HTTP_409_CONFLICT,
    )


class GameViewSet(viewsets.GenericViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_permissions(self):
        if self.action == "search":
            return [IsAdmin()]
        return super().get_permissions()

    @extend_schema(
        request=GameCreateSerializer,
        responses={
            201: GameSerializer,
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
        return Response(GameSerializer(game).data, status=status.HTTP_201_CREATED)

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
