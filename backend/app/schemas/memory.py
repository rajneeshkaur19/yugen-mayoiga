from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal["short_term", "long_term", "emotional", "player_choice"]
MemoryStatus = Literal["normal", "cracked", "gilded"]


# ─── Memory ──────────────────────────────────────────────────────────────────

class MemoryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    character_id: int
    event: str = Field(min_length=1)
    type: MemoryType
    importance: int = Field(default=50, ge=0, le=100)
    emotional_weight: int = Field(default=0, ge=-100, le=100)
    status: MemoryStatus = "normal"
    created_turn: int = Field(ge=0)
    embedding: Optional[List[float]] = None


class MemoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    importance: Optional[int] = Field(default=None, ge=0, le=100)
    emotional_weight: Optional[int] = Field(default=None, ge=-100, le=100)
    status: Optional[MemoryStatus] = None


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    character_id: int
    event: str
    type: MemoryType
    importance: int
    emotional_weight: int
    status: MemoryStatus
    created_turn: int
    embedding: Optional[List[float]]
