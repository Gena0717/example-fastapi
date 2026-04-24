from pydantic import EmailStr
from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship
from typing import List


class Users(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, nullable=False)
    username: str = Field(index=True, unique=True, nullable=False)
    email: EmailStr = Field(index=True, unique=True, nullable=False)
    password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)
    posts: List["Posts"] = Relationship(back_populates="owner")

class Posts(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, nullable=False)
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    author_id: int = Field(foreign_key="users.id", ondelete="CASCADE", nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)
    owner: Users = Relationship(back_populates="posts")

class Votes(SQLModel, table=True):
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE", primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE", primary_key=True)