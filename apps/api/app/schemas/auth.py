from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int = 3600
    token_type: str = "Bearer"


class RefreshResponse(BaseModel):
    access_token: str
    expires_in: int = 3600
