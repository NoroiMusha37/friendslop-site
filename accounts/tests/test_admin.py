import pytest
from django.test import Client

from accounts.models import User

USERS_ADMIN_URL = "/admin/accounts/user/"


@pytest.fixture
def panel(admin):
    client = Client()
    client.force_login(admin)
    return client


def test_admin_action_skips_users_it_cant_change(panel, admin, user):
    response = panel.post(
        USERS_ADMIN_URL,
        {"action": "ban_users", "_selected_action": [user.pk, admin.pk]},
        follow=True,
    )

    user.refresh_from_db()
    admin.refresh_from_db()
    assert user.status == "banned"
    assert admin.status == "active"
    messages = [str(m) for m in response.context["messages"]]
    assert "admin: Admins can't be banned." in messages


def test_superuser_cant_be_deleted_with_delete_button(panel, admin):
    panel.post(f"{USERS_ADMIN_URL}{admin.pk}/delete/", {"post": "yes"})

    assert User.objects.filter(pk=admin.pk).exists()


def test_superuser_cant_be_deleted_with_bulk_action(panel, admin, user):
    panel.post(
        USERS_ADMIN_URL,
        {
            "action": "delete_selected",
            "_selected_action": [admin.pk, user.pk],
            "post": "yes",
        },
    )

    assert User.objects.filter(pk=admin.pk).exists()


def test_regular_user_can_still_be_deleted(panel, user):
    panel.post(f"{USERS_ADMIN_URL}{user.pk}/delete/", {"post": "yes"})

    assert not User.objects.filter(pk=user.pk).exists()
