from django.test import Client


def test_admin_action_skips_users_it_cant_change(admin, user):
    client = Client()
    client.force_login(admin)

    response = client.post(
        "/admin/accounts/user/",
        {"action": "ban_users", "_selected_action": [user.pk, admin.pk]},
        follow=True,
    )

    user.refresh_from_db()
    admin.refresh_from_db()
    assert user.status == "banned"
    assert admin.status == "active"
    messages = [str(m) for m in response.context["messages"]]
    assert "admin: Admins can't be banned." in messages
