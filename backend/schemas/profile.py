from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserProfileCreate(BaseModel):
    style: str
    favorite_color: str
    body_type: str
    season: str
    favorite_colors: List[str] = Field(default_factory=list)
    style_tags: List[str] = Field(default_factory=list)
    fit_tags: List[str] = Field(default_factory=list)
    avoid_colors: List[str] = Field(default_factory=list)
    occasion_preferences: List[str] = Field(default_factory=list)


class UserProfileUpdate(BaseModel):
    style: Optional[str] = None
    favorite_color: Optional[str] = None
    body_type: Optional[str] = None
    season: Optional[str] = None
    favorite_colors: Optional[List[str]] = None
    style_tags: Optional[List[str]] = None
    fit_tags: Optional[List[str]] = None
    avoid_colors: Optional[List[str]] = None
    occasion_preferences: Optional[List[str]] = None


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
