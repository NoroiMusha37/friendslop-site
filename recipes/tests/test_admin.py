from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from recipes.models import RecipeComment


def test_recipe_page_queries_dont_grow_with_comments(client, admin, user, recipe):
    client.force_login(admin)
    url = reverse("admin:recipes_recipe_change", args=[recipe.pk])
    RecipeComment.objects.create(recipe=recipe, author=user, text="First")
    client.get(url)  # fills Django's one-time caches, so both counts below compare the same work

    with CaptureQueriesContext(connection) as one_comment:
        client.get(url)
    for _ in range(3):
        RecipeComment.objects.create(recipe=recipe, author=user, text="More")
    with CaptureQueriesContext(connection) as many_comments:
        client.get(url)

    assert len(many_comments) == len(one_comment)
