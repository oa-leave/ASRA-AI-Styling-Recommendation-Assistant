from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    feedback_type: str = Field(pattern="^(like|dislike)$")
    outfit_score: int = 0
    outfit_snapshot: Dict[str, Any] = {}
    reason: List[str] = []


class FeedbackResponse(BaseModel):
    id: int
    user_id: int
    feedback_type: str
    outfit_score: int
    outfit_snapshot: Dict[str, Any]
    reason: List[str]

    model_config = ConfigDict(from_attributes=True)
