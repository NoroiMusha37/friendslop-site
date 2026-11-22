import pytest
import responses
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User

PASSWORD = "Strong-pass-2026"


@pytest.fixture(autouse=True)
def clear_rate_limits():
    # Rate-limit counters live in the cache; without this, calls from earlier tests count against later ones
    cache.clear()


@pytest.fixture
def youtube():
    """Fake YouTube API: register replies with `youtube.get(API_URL, ...)`; real requests are blocked."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


def youtube_video(video_id, title="Video", duration="PT4M13S"):
    """One item of a YouTube `videos.list` reply."""
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "thumbnails": {
                "high": {"url": f"https://i.ytimg.com/vi/{video_id}/hq.jpg"},
            },
        },
        "contentDetails": {"duration": duration},
    }


@pytest.fixture
def admin(db):
    return User.objects.create_superuser(
        "admin",
        "admin@example.com",
        PASSWORD,
    )


@pytest.fixture
def friend(db):
    return User.objects.create_superuser(
        "friend",
        "friend@example.com",
        PASSWORD,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(
        "user",
        "user@example.com",
        PASSWORD,
        approved_at=timezone.now(),
    )


@pytest.fixture
def pending_user(db):
    return User.objects.create_user(
        "pending",
        "pending@example.com",
        PASSWORD,
        is_active=False,
    )


@pytest.fixture
def banned_user(db):
    return User.objects.create_user(
        "banned",
        "banned@example.com",
        PASSWORD,
        is_active=False,
        approved_at=timezone.now(),
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_client(admin):
    client = APIClient()
    client.force_authenticate(admin)
    return client


@pytest.fixture
def user_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client
