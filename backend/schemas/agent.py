from typing import Optional

from pydantic import BaseModel, Field


class AgentRecommendRequest(BaseModel):
    city: str = Field(min_length=1, max_length=100)
    occasion: str = Field(min_length=1, max_length=50)
    style: Optional[str] = Field(default=None, max_length=50)
