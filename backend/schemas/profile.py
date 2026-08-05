from typing import List

from pydantic import BaseModel, ConfigDict, field_validator


class UserProfileCreate(BaseModel):
    style: str
    favorite_color: str
    body_type: str
    season: str
    favorite_colors: List[str] = []
    style_tags: List[str] = []
    fit_tags: List[str] = []
    avoid_colors: List[str] = []
    occasion_preferences: List[str] = []


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    style: str
    favorite_color: str
    favorite_colors: List[str]
    style_tags: List[str]
    fit_tags: List[str]
    avoid_colors: List[str]
    occasion_preferences: List[str]
    body_type: str
    season: str

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "favorite_colors",
        "style_tags",
        "fit_tags",
        "avoid_colors",
        "occasion_preferences",
        mode="before",
    )
    @classmethod
    def ensure_list(cls, value):
        return value or []
