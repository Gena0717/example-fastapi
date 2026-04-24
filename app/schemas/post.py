from datetime import datetime
from typing import Literal

from sqlmodel import SQLModel

from app.schemas.user import UserResponse


class PostBase(SQLModel):
    title: str
    content: str


class PostCreate(PostBase):
    author_id: int | None = None


class PostResponse(PostBase):
    id: int
    created_at: datetime
    author_id: int
    owner: UserResponse


class PostUpdate(PostBase):
    title: str | None = None
    content: str | None = None


class PostWithVotes(PostResponse):
    votes: int = 0


class Vote(SQLModel):
    post_id: int
    dir: Literal[0, 1]
