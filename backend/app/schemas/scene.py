from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Scene ───────────────────────────────────────────────────────────────────

class SceneCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scene_number: int = Field(ge=1)
    content: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=100)
    mood: str = Field(min_length=1, max_length=50)
    haiku: Optional[str] = None
    is_ending: bool = False


class SceneUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: Optional[str] = Field(default=None, min_length=1)
    location: Optional[str] = Field(default=None, min_length=1, max_length=100)
    mood: Optional[str] = Field(default=None, min_length=1, max_length=50)
    haiku: Optional[str] = None
    is_ending: Optional[bool] = None


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    scene_number: int
    content: str
    location: str
    mood: str
    haiku: Optional[str]
    is_ending: bool
    created_at: datetime
