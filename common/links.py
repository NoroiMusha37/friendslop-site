"""Adding links to any object whose links (a `BaseLink` subclass) are reachable as `links`."""

from datetime import timedelta

from rest_framework import serializers

from common.schemas import YouTubeVideo
from common.youtube import YouTubeUnavailable, extract_video_id, fetch_videos, is_youtube


def prepare_links(urls: list[str], existing_urls=()) -> list[dict]:
    """Checks the urls and fetches YouTube info for all of them in one go; nothing is saved here.

    Links already added to the object, or repeated in the list, are saved once. Errors are keyed by the link's
    position in the list, so the frontend knows which link is wrong.
    """
    errors: dict[int, str] = {}  # position -> message
    video_ids: dict[int, str] = {}  # position -> YouTube video id
    kept = [i for i, url in enumerate(urls) if url not in existing_urls and url not in urls[:i]]

    for index in kept:
        url = urls[index]
        if is_youtube(url):
            video_id = extract_video_id(url)
            if video_id:
                video_ids[index] = video_id
            else:
                errors[index] = "Not a valid YouTube video link."
    if errors:
        raise position_errors(errors)

    try:
        videos = fetch_videos(list(dict.fromkeys(video_ids.values()))) if video_ids else {}
    except YouTubeUnavailable:
        videos = None  # saved without info; the daily refresh command fills it in

    if videos is not None:
        missing = {index: "YouTube video not found." for index, vid in video_ids.items() if vid not in videos}
        if missing:
            raise position_errors(missing)

    links = []
    for index in kept:
        link: dict[str, str | timedelta | None] = {
            "url": urls[index],
            "title": "",
            "duration": None,
            "thumbnail_url": "",
        }
        if videos and index in video_ids:
            video = videos[video_ids[index]]
            link.update(title=video.title, duration=video.duration, thumbnail_url=video.thumbnail_url)
        links.append(link)
    return links


def position_errors(errors: dict[int, str]) -> serializers.ValidationError:
    """Same shape as DRF's own list errors: {"<position>": ["message"]}."""
    return serializers.ValidationError({str(index): [message] for index, message in errors.items()})


def save_links(owner, prepared_links: list[dict]):
    links = owner.links
    return links.model.objects.bulk_create(
        [links.model(**{links.field.name: owner}, **data) for data in prepared_links]
    )
