from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class StoryActionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    choice_id: Optional[int] = None
    free_text: Optional[str] = Field(default=None, max_length=500)
    character_id: Optional[int] = None


class AchievedEndingSummary(BaseModel):
    id: int
    name: str
    seal_text: str


class StoryActionResponse(BaseModel):
    story_id: int
    turn_number: int
    current_scene_id: int
    scene_content: str
    scene_location: str
    scene_mood: str
    is_ending: bool
    yugen_meter: int
    applied_effects: dict[str, Any]
    triggered_events: list[str]
    achieved_endings: list[AchievedEndingSummary]


class StoryStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    story_id: int
    current_scene_id: int
    turn_number: int
    yugen_meter: int
    world_state: dict[str, Any]
    characters: dict[int, Any]
    relationships: dict[str, Any]


class YugenMeterRead(BaseModel):
    story_id: int
    yugen_meter: int
    mystery_description: str
