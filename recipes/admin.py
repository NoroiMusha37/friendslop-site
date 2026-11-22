from django.contrib import admin

from common.admin import AdminOwnerInline
from recipes.models import Ingredient, Recipe, RecipeComment, RecipeImage, RecipeIngredient, RecipeLink, RecipeReview


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    autocomplete_fields = ["ingredient"]
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("recipe", "ingredient")


class RecipeLinkInline(admin.TabularInline):
    model = RecipeLink
    extra = 0


class RecipeImageInline(admin.TabularInline):
    model = RecipeImage
    extra = 0


class RecipeReviewInline(AdminOwnerInline, admin.TabularInline):
    model = RecipeReview
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author")


class ViewAndDeleteOnly:
    """Comments come only from users through the API and are never edited, so admins can only read and delete them."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class RecipeCommentInline(ViewAndDeleteOnly, admin.TabularInline):
    model = RecipeComment
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("recipe", "author")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "cooking_method")
    search_fields = ("title",)
    inlines = [
        RecipeIngredientInline,
        RecipeLinkInline,
        RecipeImageInline,
        RecipeReviewInline,
        RecipeCommentInline,
    ]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(RecipeComment)
class RecipeCommentAdmin(ViewAndDeleteOnly, admin.ModelAdmin):
    list_display = ("recipe", "author", "created_at")
