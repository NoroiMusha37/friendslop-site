from django.db import transaction
from rest_framework import serializers

from common.links import prepare_links, save_links
from common.serializers import LinkSerializer, RatingsMixin, ReviewSerializer
from recipes.models import Ingredient, Recipe, RecipeImage
from recipes.signals import delete_file_after_commit

MAX_IMAGE_SIZE = 5 * 1024 * 1024


class UploadedImageField(serializers.ImageField):
    """An uploaded image of at most 5 MB. HEIC is refused with a clear message: most browsers can't show it."""

    def to_internal_value(self, data):
        # Checked before DRF's own image check, which would only say "not a valid image"
        if (
            getattr(
                data,
                "name",
                "",
            )
            .lower()
            .endswith((".heic", ".heif"))
        ):
            raise serializers.ValidationError("HEIC photos aren't supported. Please upload a JPEG or PNG.")
        image = super().to_internal_value(data)
        if image.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("Image must be 5 MB or smaller.")
        return image


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name")


class RecipeImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecipeImage
        fields = ("id", "image")


class RecipeListSerializer(RatingsMixin, serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            "id",
            "title",
            "cooking_method",
            "cover_image",
            "ratings",
            "combined_rating",
        )


class RecipeDetailSerializer(RatingsMixin, serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True, read_only=True)
    images = RecipeImageSerializer(many=True, read_only=True)
    links = LinkSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
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
    ingredients = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Ingredient.objects.all(),
        allow_empty=False,
    )
    cover_image = UploadedImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            "title",
            "instructions",
            "cooking_method",
            "ingredients",
            "cover_image",
        )

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        if "cover_image" in validated_data and instance.cover_image:
            # The new upload (or null) replaces the old file
            delete_file_after_commit(instance.cover_image)
        for field, value in validated_data.items():
            setattr(
                instance,
                field,
                value,
            )
        instance.save()
        if ingredients is not None:
            instance.ingredients.set(ingredients)
        return instance


class RecipeCreateSerializer(RecipeWriteSerializer):
    """Creating also takes an optional list of links; links are added later through `POST .../links/`."""

    links = serializers.ListField(
        child=serializers.URLField(max_length=500),
        required=False,
        write_only=True,
    )

    class Meta(RecipeWriteSerializer.Meta):
        fields = (*RecipeWriteSerializer.Meta.fields, "links")

    @staticmethod
    def validate_links(urls):
        # Checked (and YouTube asked) before anything is written
        return prepare_links(urls)

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        links = validated_data.pop("links", [])
        with transaction.atomic():
            recipe = Recipe.objects.create(**validated_data)
            recipe.ingredients.set(ingredients)
            save_links(recipe, links)
        return recipe


class AddImagesSerializer(serializers.Serializer):
    """Body of `POST /recipes/{id}/images/`: one or more files under `images`."""

    images = serializers.ListField(child=UploadedImageField(), allow_empty=False)
