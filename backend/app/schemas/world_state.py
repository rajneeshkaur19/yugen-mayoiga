from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class WorldStateUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=1, max_length=100)
    value: Any


class WorldStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    key: str
    value: Any
    updated_at: datetime
