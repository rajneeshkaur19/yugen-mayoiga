from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StoryLength = Literal["short", "medium", "long"]
StoryStatus = Literal["active", "completed", "abandoned"]


class StoryCreate(BaseModel):
    """Validated data required to create a story."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=50)
    theme: str = Field(min_length=1, max_length=100)
    tone: str = Field(min_length=1, max_length=50)
    season: str = Field(min_length=1, max_length=30)
    length: StoryLength


class StoryUpdate(BaseModel):
    """Fields that can be updated in an existing story."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    genre: str | None = Field(default=None, min_length=1, max_length=50)
    theme: str | None = Field(default=None, min_length=1, max_length=100)
    tone: str | None = Field(default=None, min_length=1, max_length=50)
    season: str | None = Field(default=None, min_length=1, max_length=30)
    length: StoryLength | None = None
    status: StoryStatus | None = None


class StoryRead(BaseModel):
    """Story response returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    genre: str
    theme: str
    tone: str
    season: str
    length: StoryLength
    status: StoryStatus
    created_at: datetime
