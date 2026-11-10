from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


CharacterRole = str  # flexible — no enum restriction in design doc
MemoryType = Literal["short_term", "long_term", "emotional", "player_choice"]
MemoryStatus = Literal["normal", "cracked", "gilded"]


# ─── Character ───────────────────────────────────────────────────────────────

class CharacterTraitsCreate(BaseModel):
    openness: int = Field(ge=0, le=100)
    conscientiousness: int = Field(ge=0, le=100)
    extraversion: int = Field(ge=0, le=100)
    agreeableness: int = Field(ge=0, le=100)
    neuroticism: int = Field(ge=0, le=100)


class CharacterTraitsRead(CharacterTraitsCreate):
    model_config = ConfigDict(from_attributes=True)
    character_id: int


class CharacterCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=50)
    age: Optional[int] = Field(default=None, gt=0)
    background: str = Field(default="")
    goals: list[Any] = Field(default_factory=list)
    fears: list[Any] = Field(default_factory=list)
    secrets: list[Any] = Field(default_factory=list)
    traits: Optional[CharacterTraitsCreate] = None


class CharacterUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[str] = Field(default=None, min_length=1, max_length=50)
    age: Optional[int] = Field(default=None, gt=0)
    background: Optional[str] = None
    goals: Optional[list[Any]] = None
    fears: Optional[list[Any]] = None
    secrets: Optional[list[Any]] = None


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    name: str
    role: str
    age: Optional[int]
    background: str
    goals: list[Any]
    fears: list[Any]
    secrets: list[Any]
    traits: Optional[CharacterTraitsRead] = None
