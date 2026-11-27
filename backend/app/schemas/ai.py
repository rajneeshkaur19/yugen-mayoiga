from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class LocationImageGenerateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    atmosphere: Optional[str] = Field(default="Mysterious and atmospheric", max_length=100)
    visual_details: Optional[str] = Field(default=None, max_length=300)


class LocationImageGenerateResponse(BaseModel):
    success: bool
    image_url: Optional[str] = None
    prompt_used: str
    provider: Optional[str] = None
    source_type: str = "ai_generated"
    is_fallback: bool = False
    quota_exhausted: bool = False
    missing_config: Optional[str] = None
    message: str
