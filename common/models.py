from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models

REVIEW_TEXT_MAX_LENGTH = 2000


class BaseLink(models.Model):
    """A link of any site. Title, duration and thumbnail are filled in only for YouTube videos."""

    url = models.URLField(max_length=500)
    title = models.CharField(max_length=200, blank=True)
    duration = models.DurationField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.url


class BaseReview(models.Model):
    """An admin's personal review. Each concrete review adds its target and a one-per-author constraint."""

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    rating = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10)])
    text = models.TextField(max_length=REVIEW_TEXT_MAX_LENGTH, blank=True)

    class Meta:
        abstract = True
        ordering = ["author_id"]

    def __str__(self):
        return f"{self.author} ({self.rating}/10)"
