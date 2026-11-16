from django.conf import settings
from django.db import models

from common.models import BaseLink, BaseReview


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CookingMethod(models.TextChoices):
    BAKED = "BAKED"
    FRIED = "FRIED"
    BOILED = "BOILED"
    STEWED = "STEWED"
    GRILLED = "GRILLED"
    STEAMED = "STEAMED"
    RAW = "RAW"
    OTHER = "OTHER"


class Recipe(models.Model):
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    cooking_method = models.CharField(max_length=20, choices=CookingMethod)
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
    )
    cover_image = models.ImageField(upload_to="recipes/covers/", blank=True)

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    # PROTECT: an ingredient used in any recipe can't be deleted
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            ),
        ]

    def __str__(self):
        return f"{self.recipe}: {self.ingredient}"


class RecipeImage(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="recipes/images/")

    def __str__(self):
        return self.image.name


class RecipeLink(BaseLink):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="links",
    )


class RecipeReview(BaseReview):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "author"],
                name="unique_recipe_review_author",
            ),
        ]


class RecipeComment(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author} on {self.recipe}"
