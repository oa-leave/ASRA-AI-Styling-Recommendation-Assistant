from typing import List

from pydantic import BaseModel, ConfigDict


class UserProfileCreate(BaseModel):
    style: str
    favorite_color: str
    body_type: str
    season: str
    favorite_colors: List[str] = []
    style_tags: List[str] = []


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    style: str
    favorite_color: str
    favorite_colors: List[str]
    style_tags: List[str]
    body_type: str
    season: str

    model_config = ConfigDict(from_attributes=True)
