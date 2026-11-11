from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RelationshipCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    from_character: int
    to_character: int
    trust: int = Field(default=50, ge=0, le=100)
    friendship: int = Field(default=50, ge=0, le=100)
    suspicion: int = Field(default=0, ge=0, le=100)
    fear: int = Field(default=0, ge=0, le=100)
    dependency: int = Field(default=0, ge=0, le=100)


class RelationshipUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    trust: Optional[int] = Field(default=None, ge=0, le=100)
    friendship: Optional[int] = Field(default=None, ge=0, le=100)
    suspicion: Optional[int] = Field(default=None, ge=0, le=100)
    fear: Optional[int] = Field(default=None, ge=0, le=100)
    dependency: Optional[int] = Field(default=None, ge=0, le=100)


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    story_id: int
    from_character: int
    to_character: int
    trust: int
    friendship: int
    suspicion: int
    fear: int
    dependency: int
