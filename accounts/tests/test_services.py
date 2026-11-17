import pytest

from accounts import services
from accounts.models import User


@pytest.mark.parametrize(
    ("change", "start", "result"),
    [
        (services.approve, "pending_user", "active"),
        (services.ban, "user", "banned"),
        (services.unban, "banned_user", "active"),
    ],
)
def test_allowed_status_change(request, admin, change, start, result):
    user = request.getfixturevalue(start)

    change(user, admin)

    user.refresh_from_db()
    assert user.status == result


def test_reject_deletes_pending_user(pending_user, admin):
    services.reject(pending_user, admin)

    assert not User.objects.filter(pk=pending_user.pk).exists()


@pytest.mark.parametrize(
    ("change", "start"),
    [
        (services.approve, "user"),
        (services.approve, "banned_user"),
        (services.reject, "user"),
        (services.ban, "pending_user"),
        (services.ban, "banned_user"),
        (services.ban, "admin"),
        (services.unban, "user"),
        (services.unban, "pending_user"),
    ],
)
def test_status_change_refused_in_wrong_state(request, admin, change, start):
    user = request.getfixturevalue(start)
    status_before = user.status

    with pytest.raises(services.UserStateError):
        change(user, admin)

    user.refresh_from_db()
    assert user.status == status_before
