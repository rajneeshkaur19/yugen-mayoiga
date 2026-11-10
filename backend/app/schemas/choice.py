from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─── Choice ──────────────────────────────────────────────────────────────────

class ChoiceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    choice_text: str = Field(min_length=1)
    effects: dict[str, Any] = Field(default_factory=dict)
    condition: Optional[dict[str, Any]] = None
    allow_loop: bool = False
    sort_order: int = Field(default=0, ge=0, le=32767)
    next_scene_id: Optional[int] = None


class ChoiceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    choice_text: Optional[str] = Field(default=None, min_length=1)
    effects: Optional[dict[str, Any]] = None
    condition: Optional[dict[str, Any]] = None
    allow_loop: Optional[bool] = None
    sort_order: Optional[int] = Field(default=None, ge=0, le=32767)
    next_scene_id: Optional[int] = None


class ChoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    scene_id: int
    choice_text: str
    effects: dict[str, Any]
    condition: Optional[dict[str, Any]]
    allow_loop: bool
    sort_order: int
    next_scene_id: Optional[int]
