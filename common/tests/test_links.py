from datetime import timedelta

import pytest
import requests
from rest_framework.exceptions import ValidationError

from common.links import prepare_links
from common.youtube import API_URL, YouTubeConfigError, extract_video_id
from conftest import youtube_video

VIDEO = "dQw4w9WgXcQ"
OTHER_VIDEO = "9bZkp7q19f0"


@pytest.mark.parametrize(
    ("url", "video_id"),
    [
        (f"https://www.youtube.com/watch?v={VIDEO}", VIDEO),
        (f"https://youtube.com/watch?v={VIDEO}&t=42", VIDEO),
        (f"https://www.youtube.com/watch?feature=share&v={VIDEO}", VIDEO),
        (f"https://WWW.YouTube.com/watch?v={VIDEO}", VIDEO),
        (f"https://m.youtube.com/watch?v={VIDEO}", VIDEO),
        (f"https://youtu.be/{VIDEO}?si=abc", VIDEO),
        (f"https://www.youtube.com/shorts/{VIDEO}", VIDEO),
        (f"https://www.youtube.com/embed/{VIDEO}", VIDEO),
        (f"https://www.youtube.com/live/{VIDEO}", VIDEO),
        ("https://www.youtube.com/@somechannel", None),
        ("https://www.youtube.com/watch?v=tooshort", None),
    ],
)
def test_extract_video_id(url, video_id):
    assert extract_video_id(url) == video_id


def test_youtube_info_is_fetched_in_one_call(youtube):
    youtube.get(API_URL, json={"items": [youtube_video(VIDEO, title="Rick"), youtube_video(OTHER_VIDEO, title="Psy")]})
    urls = [
        f"https://youtu.be/{VIDEO}",
        f"https://www.youtube.com/watch?v={OTHER_VIDEO}",
        "https://instagram.com/reel/x",
    ]

    links = prepare_links(urls)

    assert len(youtube.calls) == 1
    assert links[0] == {
        "url": urls[0],
        "title": "Rick",
        "duration": timedelta(minutes=4, seconds=13),
        "thumbnail_url": f"https://i.ytimg.com/vi/{VIDEO}/hq.jpg",
    }
    assert links[1]["title"] == "Psy"
    assert links[2] == {"url": urls[2], "title": "", "duration": None, "thumbnail_url": ""}


def test_youtube_link_without_video_is_reported_by_position(youtube):
    with pytest.raises(ValidationError) as error:
        prepare_links(["https://a.com", "https://www.youtube.com/@channel"])

    assert error.value.detail == {"1": ["Not a valid YouTube video link."]}
    assert not youtube.calls


def test_repeated_and_already_added_links_are_saved_once(youtube):
    links = prepare_links(["https://a.com", "https://b.com", "https://b.com"], existing_urls={"https://a.com"})

    assert [link["url"] for link in links] == ["https://b.com"]


def test_missing_video_is_rejected(youtube):
    youtube.get(API_URL, json={"items": []})

    with pytest.raises(ValidationError) as error:
        prepare_links(["https://a.com", f"https://youtu.be/{VIDEO}"])

    assert error.value.detail == {"1": ["YouTube video not found."]}


@pytest.mark.parametrize(
    "reply",
    [
        {"status": 503},
        {"status": 403, "json": {"error": {"errors": [{"reason": "quotaExceeded"}]}}},
        {"body": requests.ConnectionError()},
    ],
    ids=["server-error", "quota-used-up", "unreachable"],
)
def test_youtube_down_saves_link_without_info(youtube, reply):
    youtube.get(API_URL, **reply)

    links = prepare_links([f"https://youtu.be/{VIDEO}"])

    assert links[0]["title"] == ""


def test_invalid_api_key_blocks_saving(youtube):
    youtube.get(API_URL, status=400, json={"error": {"errors": [{"reason": "badRequest"}]}})

    with pytest.raises(YouTubeConfigError):
        prepare_links([f"https://youtu.be/{VIDEO}"])
