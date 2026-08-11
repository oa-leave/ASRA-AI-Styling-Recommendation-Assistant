from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=200)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
