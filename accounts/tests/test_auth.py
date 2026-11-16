import pytest
from django.urls import reverse

from accounts.models import User
from conftest import PASSWORD


def register(client, **overrides):
    data = {
        "username": "newbie",
        "email": "newbie@example.com",
        "password": PASSWORD,
        "password2": PASSWORD,
    }
    return client.post(reverse("register"), {**data, **overrides})


def login(client, username, password=PASSWORD):
    return client.post(reverse("login"), {"username": username, "password": password})


@pytest.mark.django_db
def test_register_creates_pending_inactive_user(api_client):
    response = register(api_client)

    assert response.status_code == 201
    user = User.objects.get(username="newbie")
    assert user.status == "pending"
    assert not user.is_active


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"password2": "Other-pass-2026"}, "password2"),
        ({"password": "password", "password2": "password"}, "password"),
    ],
    ids=["passwords-differ", "weak-password"],
)
def test_register_rejects_bad_password(api_client, overrides, field):
    response = register(api_client, **overrides)

    assert response.status_code == 400
    assert field in response.json()
    assert not User.objects.filter(username="newbie").exists()


@pytest.mark.parametrize(
    ("username_fixture", "message"),
    [("pending_user", "waiting for admin approval"), ("banned_user", "banned")],
)
def test_login_explains_why_inactive_user_cant_log_in(
    api_client,
    request,
    username_fixture,
    message,
):
    user = request.getfixturevalue(username_fixture)

    response = login(api_client, user.username)

    assert response.status_code == 401
    assert message in response.json()["detail"]


def test_login_with_wrong_password_reveals_nothing(api_client, pending_user):
    response = login(
        api_client,
        pending_user.username,
        password="wrong",
    )

    assert response.status_code == 401
    assert "waiting" not in response.json()["detail"]


def test_approved_user_gets_tokens(api_client, user):
    response = login(api_client, user.username)

    assert response.status_code == 200
    assert {"access", "refresh"} <= response.json().keys()


@pytest.mark.parametrize(
    ("username_fixture", "is_admin"),
    [("user", False), ("admin", True)],
)
def test_me_reports_admin_flag(api_client, request, username_fixture, is_admin):
    api_client.force_authenticate(request.getfixturevalue(username_fixture))

    assert api_client.get(reverse("me")).json()["is_admin"] is is_admin


def test_banning_blocks_existing_tokens(api_client, user):
    # Banning relies on tokens being refused for inactive users, not on a blacklist
    tokens = login(api_client, user.username).json()
    user.is_active = False
    user.save()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api_client.get(reverse("me")).status_code == 401
    api_client.credentials()
    assert api_client.post(reverse("refresh"), {"refresh": tokens["refresh"]}).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ["login", "register"])
def test_auth_endpoints_are_rate_limited(api_client, url_name):
    statuses = [api_client.post(reverse(url_name), {}).status_code for _ in range(6)]

    assert 429 not in statuses[:5]
    assert statuses[5] == 429


def test_api_docs_are_admin_only(api_client, user, admin):
    api_client.force_login(user)
    assert api_client.get(reverse("docs")).status_code == 403

    api_client.force_login(admin)
    assert api_client.get(reverse("docs")).status_code == 200
