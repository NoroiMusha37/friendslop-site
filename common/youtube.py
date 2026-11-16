"""YouTube Data API v3 client: recognizes video links and fetches their title, duration and thumbnail."""

import re

import requests
from django.conf import settings
from rest_framework.exceptions import APIException

from common.schemas import YouTubeVideo, YouTubeVideoList

API_URL = "https://www.googleapis.com/youtube/v3/videos"
BATCH_SIZE = 50  # the API accepts up to 50 ids per call
TIMEOUT_SECONDS = 5
_HOST = r"https?://(?:(?:www\.|m\.)?youtube\.com|(?:www\.)?youtu\.be)"
YOUTUBE_URL = re.compile(_HOST + r"(?:[/?#]|$)", re.IGNORECASE)
# watch?v=ID (v may come after other parameters), youtu.be/ID, /shorts/ID, /embed/ID, /live/ID
VIDEO_URL = re.compile(
    r"https?://(?:(?:www\.|m\.)?youtube\.com/(?:watch\?(?:[^#]*&)?v=|shorts/|embed/|live/)|(?:www\.)?youtu\.be/)"
    r"([A-Za-z0-9_-]{11})(?:[?&#/]|$)",
    re.IGNORECASE,
)
# Errors that mean "try again later"
TEMPORARY_REASONS = {
    "quotaExceeded",
    "rateLimitExceeded",
    "dailyLimitExceeded",
    "userRateLimitExceeded",
}


class YouTubeUnavailable(Exception):
    """YouTube can't be reached right now; links are saved without info and filled in later."""


class YouTubeUnavailableError(APIException):
    """Answer of the refresh endpoints when YouTube still can't be reached; nothing is changed."""

    status_code = 503
    default_detail = "YouTube can't be reached right now. Try again later."
    default_code = "youtube_unavailable"


class YouTubeConfigError(APIException):
    status_code = 503
    default_detail = "YouTube API key is invalid or not allowed. Check YOUTUBE_API_KEY."
    default_code = "youtube_config_error"


def is_youtube(url: str) -> bool:
    return bool(YOUTUBE_URL.match(url))


def extract_video_id(url: str) -> str | None:
    """The 11-character video id, or None if the YouTube link doesn't point to a video."""
    match = VIDEO_URL.match(url)
    return match.group(1) if match else None


def fetch_videos(video_ids: list[str]) -> dict[str, YouTubeVideo]:
    """Info for the given ids; ids of videos that don't exist are missing from the result."""
    videos = {}
    for start in range(
        0,
        len(video_ids),
        BATCH_SIZE,
    ):
        batch = video_ids[start : start + BATCH_SIZE]
        params = {
            "part": "snippet,contentDetails",
            "id": ",".join(batch),
            "key": settings.YOUTUBE_API_KEY,
        }

        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            raise YouTubeUnavailable from e

        if response.status_code >= 500:
            raise YouTubeUnavailable
        if response.status_code >= 400:
            try:
                errors = response.json().get("error", {}).get("errors", [])
            except ValueError:
                errors = []
            reasons = {error.get("reason") for error in errors}
            if reasons & TEMPORARY_REASONS:
                raise YouTubeUnavailable
            raise YouTubeConfigError

        videos.update(
            {video.id: video for video in YouTubeVideoList.model_validate(response.json()).items},
        )
    return videos
