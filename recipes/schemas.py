from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError


class RandomIngredientsQuery(BaseModel):
    """Query parameters of `GET /ingredients/random/`."""

    mode: Literal["naive", "smart"]
    size: int = Field(5, ge=2, le=20)
    include: list[int] = []

    @field_validator("include", mode="before")
    @classmethod
    def split_ids(cls, value):
        # Comes as "12,40,7" in the URL
        return [part for part in value.split(",") if part.strip()] if isinstance(value, str) else value

    @field_validator("include")
    @classmethod
    def at_most_size(cls, value: list[int], info: ValidationInfo) -> list[int]:
        value = list(dict.fromkeys(value))  # an id given twice counts once
        if "size" in info.data and len(value) > info.data["size"]:
            raise PydanticCustomError("too_many", "More ingredients to include than `size`.")
        return value
