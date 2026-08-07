from typing import Optional

from pydantic import BaseModel, Field


class AgentRecommendRequest(BaseModel):
    query: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = Field(default=None, max_length=100)
    occasion: Optional[str] = Field(default=None, max_length=50)
    style: Optional[str] = Field(default=None, max_length=50)
