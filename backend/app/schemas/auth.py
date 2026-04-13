"""Auth schemas."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    firm_id: int
    firm_name: str | None = None

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str
