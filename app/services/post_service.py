from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.db import get_session
from app.models import Posts, Users, Votes
from app.schemas.post import PostCreate, PostUpdate, PostWithVotes
from app.services import auth_service

router = APIRouter()
db_session = Annotated[Session, Depends(get_session)]


async def create_post(
    payload: PostCreate,
    session: db_session,
    current_user: Annotated[Users, Depends(auth_service.get_current_user)],
):
    payload.author_id = int(current_user.id)
    post = Posts.model_validate(payload)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


async def get_posts(
    session: db_session,
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = None,
    topic: Optional[str] = None,
):
    query = (
        select(Posts, func.count(Votes.post_id).label("votes"))
        .join(Votes, Votes.post_id == Posts.id, isouter=True)
        .group_by(Posts.id)
    )
    if search:
        query = query.where(Posts.content.ilike(f"%{search}%"))
    if topic:
        query = query.where(Posts.title.ilike(f"%{topic}%"))

    result = session.exec(query.offset(skip).limit(limit))
    posts = [
        PostWithVotes(**post.model_dump(), votes=votes, owner=post.owner)
        for post, votes in result.all()
    ]
    return posts


async def get_post(post_id: int, session: db_session):
    query = (
        select(Posts, func.count(Votes.post_id).label("votes"))
        .join(Votes, Votes.post_id == Posts.id, isouter=True)
        .group_by(Posts.id)
    )
    result = session.exec(query.where(Posts.id == post_id)).first()
    if not result:
        raise HTTPException(status_code=404, detail=f"Post with ID {post_id} not found")

    post_obj, votes = result    
    post = PostWithVotes(**post_obj.model_dump(), votes=votes, owner=post_obj.owner)    
    return post


async def update_post(
    post_id: int,
    payload: PostUpdate,
    session: db_session,
    current_user: Annotated[Users, Depends(auth_service.get_current_user)],
):
    post = session.get(Posts, post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with ID {post_id} not found")
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You do not have permission to update this post"
        )
    post.sqlmodel_update(payload.model_dump(exclude_unset=True))
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


async def delete_post(
    post_id: int,
    session: db_session,
    current_user: Annotated[Users, Depends(auth_service.get_current_user)],
):
    post = session.get(Posts, post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with ID {post_id} not found")
    if post.author_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="You do not have permission to delete this post"
        )
    session.delete(post)
    session.commit()
    return {"message": f"Post with ID {post_id} deleted successfully"}
