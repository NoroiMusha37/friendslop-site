from django import forms
from django.contrib import admin

from games.models import Game, GameCategory, GameReview, GameStatus


class GameAdminForm(forms.ModelForm):
    categories = forms.MultipleChoiceField(
        choices=GameCategory,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Game
        fields = ["categories"]


class GameStatusInline(admin.TabularInline):
    model = GameStatus
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("game", "user")


class GameReviewInline(admin.TabularInline):
    model = GameReview
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("author")


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """Games come only from RAWG, so here they can be viewed and deleted, and only their categories edited."""

    form = GameAdminForm
    inlines = [GameStatusInline, GameReviewInline]
    list_display = ("name", "release_date", "rawg_rating")
    search_fields = ("name",)
    fields = (
        "name",
        "rawg_id",
        "categories",
        "genres",
        "release_date",
        "rawg_rating",
        "cover_url",
        "description",
    )
    readonly_fields = (
        "name",
        "rawg_id",
        "genres",
        "release_date",
        "rawg_rating",
        "cover_url",
        "description",
    )

    def has_add_permission(self, request):
        return False
