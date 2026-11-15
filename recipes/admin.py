from django.contrib import admin

from recipes.models import Ingredient, Recipe, RecipeComment, RecipeImage, RecipeIngredient, RecipeLink, RecipeReview


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    autocomplete_fields = ["ingredient"]
    extra = 0


class RecipeLinkInline(admin.TabularInline):
    model = RecipeLink
    extra = 0


class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 0


class RecipeReviewInline(admin.TabularInline):
    model = RecipeReview
    extra = 0


class RecipeCommentInline(admin.TabularInline):
    model = RecipeComment
    extra = 0


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "cooking_method")
    search_fields = ("title",)
    inlines = [RecipeIngredientInline, RecipeLinkInline, RecipeImageInline, RecipeReviewInline, RecipeCommentInline]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(RecipeComment)
class RecipeCommentAdmin(admin.ModelAdmin):
    list_display = ("recipe", "author", "created_at")
