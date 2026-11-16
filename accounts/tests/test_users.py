import pytest
from django.urls import reverse

from accounts.models import User

USERS_URL = reverse("user-list")


def action_url(user, action):
    return reverse(f"user-{action}", args=[user.pk])


def usernames(response):
    return {u["username"] for u in response.json()}


def test_list_hides_superusers(admin_client, user, pending_user):
    assert usernames(admin_client.get(USERS_URL)) == {"user", "pending"}


@pytest.mark.parametrize(
    ("status", "expected"),
    [("pending", {"pending"}), ("active", {"user"}), ("banned", {"banned"})],
)
def test_list_filters_by_status(
    admin_client,
    user,
    pending_user,
    banned_user,
    status,
    expected,
):
    assert usernames(admin_client.get(USERS_URL, {"status": status})) == expected


def test_action_returns_updated_user(admin_client, pending_user):
    response = admin_client.post(action_url(pending_user, "approve"))

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_action_in_wrong_state_gives_400(admin_client, user):
    response = admin_client.post(action_url(user, "approve"))

    assert response.status_code == 400
    assert response.json()["detail"] == "Only pending users can be approved."


def test_reject_returns_204(admin_client, pending_user):
    assert admin_client.post(action_url(pending_user, "reject")).status_code == 204
    assert not User.objects.filter(pk=pending_user.pk).exists()


@pytest.mark.parametrize(
    ("client_fixture", "status"),
    [("api_client", 401), ("user_client", 403)],
)
def test_only_admins_manage_users(request, pending_user, client_fixture, status):
    client = request.getfixturevalue(client_fixture)

    assert client.get(USERS_URL).status_code == status
    assert client.post(action_url(pending_user, "approve")).status_code == status
