import pytest
from django.contrib.admin import site
from django.urls import reverse

from games.admin import GameReviewInline, GameStatusInline
from games.models import Game, GameCategory, GameReview, GameStatus

# Django expects these counters for the status and review sections on every save of the game page
EMPTY_SECTIONS = {
    "statuses-TOTAL_FORMS": 0,
    "statuses-INITIAL_FORMS": 0,
    "reviews-TOTAL_FORMS": 0,
    "reviews-INITIAL_FORMS": 0,
}


@pytest.fixture
def admin_panel(client, admin):
    client.force_login(admin)
    return client


@pytest.mark.parametrize(
    ("inline_class", "model", "owner"),
    [
        (GameStatusInline, GameStatus, "user"),
        (GameReviewInline, GameReview, "author"),
    ],
)
def test_status_and_review_owner_can_only_be_an_admin(admin, user, inline_class, model, owner):
    inline = inline_class(Game, site)

    field = inline.formfield_for_foreignkey(model._meta.get_field(owner), None)

    assert list(field.queryset) == [admin]


def test_game_cant_be_added_in_admin_panel(admin_panel):
    response = admin_panel.get(reverse("admin:games_game_add"))

    assert response.status_code == 403


def test_admin_panel_edits_categories_but_not_rawg_data(admin_panel, game):
    response = admin_panel.post(
        reverse("admin:games_game_change", args=[game.pk]),
        {
            "categories": [GameCategory.COOP, GameCategory.MULTIPLAYER],
            "name": "Changed",
            **EMPTY_SECTIONS,
        },
    )

    assert response.status_code == 302
    game.refresh_from_db()
    assert game.categories == [GameCategory.COOP, GameCategory.MULTIPLAYER]
    assert game.name == "Portal"


def test_admin_panel_requires_a_category(admin_panel, game):
    response = admin_panel.post(
        reverse("admin:games_game_change", args=[game.pk]),
        {"categories": [], **EMPTY_SECTIONS},
    )

    assert response.status_code == 200
    game.refresh_from_db()
    assert game.categories == [GameCategory.SOLO]
