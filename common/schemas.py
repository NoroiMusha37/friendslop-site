from datetime import timedelta

from pydantic import AliasPath, BaseModel, Field


class YouTubeVideo(BaseModel):
    id: str
    title: str = Field(validation_alias=AliasPath("snippet", "title"))
    duration: timedelta = Field(validation_alias=AliasPath("contentDetails", "duration"))
    thumbnail_url: str = Field("", validation_alias=AliasPath("snippet", "thumbnails", "high", "url"))


class YouTubeVideoList(BaseModel):
    items: list[YouTubeVideo]
