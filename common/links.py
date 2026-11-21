"""Adding links to any object whose links (a `BaseLink` subclass) are reachable as `links`."""

import logging
from collections import defaultdict
from datetime import timedelta

from django.apps import apps
from rest_framework import serializers

from common.models import BaseLink
from common.youtube import (
    YouTubeUnavailable,
    YouTubeUnavailableError,
    extract_video_id,
    fetch_videos,
    is_youtube,
)

logger = logging.getLogger(__name__)


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
    except YouTubeUnavailable as e:
        videos = None  # saved without info; the refresh endpoints fill it in later
        logger.warning("YouTube unavailable (%s): %d link(s) saved without info", e, len(video_ids))

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
            link.update(
                title=video.title,
                duration=video.duration,
                thumbnail_url=video.thumbnail_url,
            )
        links.append(link)
    return links


def position_errors(errors: dict[int, str]) -> serializers.ValidationError:
    """Same shape as DRF's own list errors: {"<position>": ["message"]}."""
    return serializers.ValidationError(
        {str(index): [message] for index, message in errors.items()},
    )


def save_links(owner, prepared_links: list[dict]):
    links = owner.links
    return links.model.objects.bulk_create(
        [links.model(**{links.field.name: owner}, **data) for data in prepared_links]
    )


def link_models():
    """Every concrete link model"""
    return [model for model in apps.get_models() if issubclass(model, BaseLink)]


def owner_field(model):
    """The link's foreign key to the object it belongs to; `BaseLink` has no other."""
    return next(field for field in model._meta.fields if field.is_relation)


def fill_missing_info(links) -> tuple[int, list]:
    """Fills in the YouTube info of links saved while YouTube was down. Returns how many were filled and the links
    whose video wasn't found (removed from YouTube since); those stay without info.

    `links` may mix link models. Other sites' links never get info, so they are skipped.
    """
    pending = [(link, video_id) for link in links if not link.title and (video_id := extract_video_id(link.url))]
    try:
        videos = fetch_videos(list(dict.fromkeys(video_id for _, video_id in pending)))
    except YouTubeUnavailable as e:
        logger.warning("YouTube unavailable (%s): link info not refreshed", e)
        raise YouTubeUnavailableError from e
    filled = defaultdict(list)  # link model -> its filled links, since `links` may mix models
    not_found = []
    for link, video_id in pending:
        if video_id not in videos:
            not_found.append(link)
            continue
        video = videos[video_id]
        link.title = video.title
        link.duration = video.duration
        link.thumbnail_url = video.thumbnail_url
        filled[type(link)].append(link)
    for model, model_links in filled.items():
        model.objects.bulk_update(model_links, ["title", "duration", "thumbnail_url"])
    if not_found:
        logger.info("Videos removed from YouTube, links left without info: %s", [link.url for link in not_found])
    return sum(len(model_links) for model_links in filled.values()), not_found
