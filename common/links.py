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


def prepare_links(urls: list[str], existing_urls=(), stored_urls=()) -> list[dict]:
    """Checks the urls and fetches YouTube info for all of them in one go; nothing is saved here.

    Links already added to the object, or repeated in the list, are saved once. `stored_urls` are rows of a shared link
    table: they already passed these checks and keep their info, so YouTube isn't asked again. Errors are keyed by the
    link's position in the list, so the frontend knows which link is wrong.
    """
    errors: dict[int, str] = {}  # position -> message
    video_ids: dict[int, str] = {}  # position -> YouTube video id
    kept = [i for i, url in enumerate(urls) if url not in existing_urls and url not in urls[:i]]

    for index in kept:
        url = urls[index]
        if url not in stored_urls and is_youtube(url):
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


def is_shared(links) -> bool:
    """Whether an object's `links` manager is many-to-many, so one link row can belong to several objects."""
    return hasattr(links, "through")


def stored_urls(model, urls: list[str]) -> set[str]:
    return set(model.objects.filter(url__in=urls).values_list("url", flat=True))


def save_links(owner, prepared_links: list[dict]):
    links = owner.links
    if not is_shared(links):
        return links.model.objects.bulk_create(
            [links.model(**{links.field.name: owner}, **data) for data in prepared_links]
        )
    # Rows that already exist keep their info; ignoring conflicts also covers two admins adding one url at once
    links.model.objects.bulk_create(
        [links.model(**data) for data in prepared_links],
        ignore_conflicts=True,
    )
    urls = [data["url"] for data in prepared_links]
    by_url = links.model.objects.in_bulk(urls, field_name="url")
    saved = [by_url[url] for url in urls]
    links.add(*saved)
    return saved


def remove_link(owner, link) -> None:
    """A shared link may serve other objects and stays reusable, so only this object's relation goes."""
    if is_shared(owner.links):
        owner.links.remove(link)
    else:
        link.delete()


def link_models():
    """Every concrete link model"""
    return [model for model in apps.get_models() if issubclass(model, BaseLink)]


def link_owners(link) -> list[tuple[str, int]]:
    """The (model name, id) of every object using this link; a shared link not attached to anything has none."""
    model = type(link)
    field = next((field for field in model._meta.fields if field.is_relation), None)
    if field:
        return [(field.related_model._meta.model_name, getattr(link, field.attname))]
    relation = next(rel for rel in model._meta.related_objects if rel.many_to_many)
    owner_ids = getattr(link, relation.get_accessor_name()).order_by("pk").values_list("pk", flat=True)
    return [(relation.related_model._meta.model_name, owner_id) for owner_id in owner_ids]


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
