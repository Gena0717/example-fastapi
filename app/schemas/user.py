from datetime import datetime

from pydantic import EmailStr
from sqlmodel import SQLModel


class UserBase(SQLModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime


class UserUpdate(UserBase):
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None

class Token(SQLModel):
    access_token: str
    token_type: str 

class TokenData(SQLModel):
    user_id: int | None = None
    email: EmailStr | None = None
