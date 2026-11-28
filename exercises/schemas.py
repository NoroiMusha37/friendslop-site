from typing import Annotated, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from exercises.models import MAX_INTENSITY, MIN_INTENSITY, LoadCategory, MuscleCategory

Intensity = Annotated[int, Field(ge=MIN_INTENSITY, le=MAX_INTENSITY)]


class RandomExercisesQuery(BaseModel):
    """Query parameters of `GET /exercises/random/`. Every filter is optional."""

    count: int = Field(default=5, ge=1, le=20)
    muscle: list[MuscleCategory] = []
    load: list[LoadCategory] = []
    intensity_min: Intensity | None = None
    intensity_max: Intensity | None = None

    @field_validator("muscle", "load", mode="before")
    @classmethod
    def split_values(cls, value):
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("intensity_min", "intensity_max", mode="before")
    @classmethod
    def empty_means_no_filter(cls, value):
        return None if value == "" else value

    @model_validator(mode="after")
    def intensity_range_is_ordered(self) -> Self:
        if (
            self.intensity_min is not None
            and self.intensity_max is not None
            and self.intensity_min > self.intensity_max
        ):
            raise ValueError("intensity_min can't be greater than intensity_max.")
        return self
