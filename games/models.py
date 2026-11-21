from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models

from common.models import BaseReview


class GameCategory(models.TextChoices):
    SOLO = "SOLO"
    COOP = "COOP"
    MULTIPLAYER = "MULTIPLAYER"


class PlayStatus(models.TextChoices):
    PLANNED = "PLANNED"
    PLAYING = "PLAYING"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"


class Genre(models.Model):
    rawg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Game(models.Model):
    rawg_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_url = models.URLField(max_length=500, blank=True)
    release_date = models.DateField(null=True, blank=True)
    rawg_rating = models.FloatField(null=True, blank=True)
    categories = ArrayField(models.CharField(max_length=20, choices=GameCategory))
    genres = models.ManyToManyField(
        Genre,
        related_name="games",
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(categories__len__gt=0),
                name="game_has_category",
            ),
            models.CheckConstraint(
                condition=models.Q(rawg_rating__gt=0, rawg_rating__lte=5),
                name="game_rawg_rating_range",
            ),
        ]

    def __str__(self):
        return self.name


class GameStatus(models.Model):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="statuses",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",  # tells Django not to create the reverse link
    )
    status = models.CharField(max_length=20, choices=PlayStatus)

    class Meta:
        ordering = ["user_id"]
        verbose_name_plural = "game statuses"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "user"],
                name="unique_game_status_user",
            ),
        ]

    def __str__(self):
        return f"{self.user}: {self.game} ({self.status})"


class GameReview(BaseReview):
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    class Meta(BaseReview.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["game", "author"],
                name="unique_game_review_author",
            ),
        ]
