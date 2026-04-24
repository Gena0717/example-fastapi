from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.models import Users
from app.schemas.post import PostCreate, PostResponse, PostUpdate, PostWithVotes
from app.services import auth_service, post_service

router = APIRouter(prefix="/posts", tags=["Posts"])
db_session = Annotated[Session, Depends(get_session)]


@router.post("/", status_code=201, response_model=PostResponse)
async def create_post(
    payload: PostCreate,
    session: db_session,
    current_user: Annotated[Users, Depends(auth_service.get_current_user)],
):
    post = await post_service.create_post(payload, session, current_user)
    return post


@router.get("/", response_model=list[PostWithVotes])
async def get_posts(session: db_session, limit: int = 10, skip: int = 0, search: Optional[str] = "", topic: Optional[str] = ""):
    posts = await post_service.get_posts(session, limit, skip, search, topic)
    return posts


@router.get("/{post_id}", response_model=PostWithVotes)
async def get_post(post_id: int, session: db_session):
    post = await post_service.get_post(post_id, session)
    return post


@router.put("/{post_id}", response_model=PostResponse)
async def update_post(post_id: int,
         payload: PostUpdate, 
         session: db_session,
         current_user: Annotated[Users, Depends(auth_service.get_current_user)]):
    post = await post_service.update_post(post_id, payload, session, current_user)
    return post


@router.delete("/{post_id}")
async def delete_post(post_id: int,
         session: db_session,
         current_user: Annotated[Users, Depends(auth_service.get_current_user)]):
    result = await post_service.delete_post(post_id, session)
    return result
