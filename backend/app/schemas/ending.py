from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EndingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    conditions: dict[str, Any]
    seal_text: str = Field(min_length=1, max_length=50)


class EndingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    name: str
    conditions: dict[str, Any]
    seal_text: str


class UserEndingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    ending_id: int
    achieved_at: datetime
