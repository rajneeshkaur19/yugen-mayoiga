from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

FeedbackType = Literal["Bug Report", "Technical Issue", "Suggestion", "Other"]


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    feedback_type: FeedbackType = "Bug Report"
    subject: str = Field(min_length=2, max_length=150)
    message: str = Field(min_length=5, max_length=2000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    feedback_type: FeedbackType
    subject: str
    created_at: datetime
    email_sent: bool = False
    message: str
