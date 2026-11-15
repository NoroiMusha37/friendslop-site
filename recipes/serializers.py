from rest_framework import serializers

from common.serializers import BaseLinkSerializer, BaseReviewSerializer, RatingsMixin
from recipes.models import Ingredient, Recipe, RecipeImage, RecipeLink, RecipeReview
from recipes.signals import delete_file_after_commit

MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_image_size(image):
    if image and image.size > MAX_IMAGE_SIZE:
        raise serializers.ValidationError("Image must be 5 MB or smaller.")


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name")


class RecipeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeImage
        fields = ("id", "image")


class RecipeLinkSerializer(BaseLinkSerializer):
    class Meta(BaseLinkSerializer.Meta):
        model = RecipeLink


class RecipeReviewSerializer(BaseReviewSerializer):
    class Meta(BaseReviewSerializer.Meta):
        model = RecipeReview


class RecipeListSerializer(RatingsMixin, serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "title", "cooking_method", "cover_image", "ratings", "combined_rating")


class RecipeDetailSerializer(RatingsMixin, serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True, read_only=True)
    images = RecipeImageSerializer(many=True, read_only=True)
    links = RecipeLinkSerializer(many=True, read_only=True)
    reviews = RecipeReviewSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            "id",
            "title",
            "instructions",
            "cooking_method",
            "cover_image",
            "ingredients",
            "images",
            "links",
            "reviews",
            "ratings",
            "combined_rating",
            "comment_count",
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    # Declared explicitly: DRF makes many-to-many fields with a custom link table read-only
    ingredients = serializers.PrimaryKeyRelatedField(many=True, queryset=Ingredient.objects.all(), allow_empty=False)
    cover_image = serializers.ImageField(required=False, allow_null=True, validators=[validate_image_size])

    class Meta:
        model = Recipe
        fields = ("title", "instructions", "cooking_method", "ingredients", "cover_image")

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)
        recipe.ingredients.set(ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        if "cover_image" in validated_data and instance.cover_image:
            # The new upload (or null) replaces the old file
            delete_file_after_commit(instance.cover_image)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if ingredients is not None:
            instance.ingredients.set(ingredients)
        return instance
