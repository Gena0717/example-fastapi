from typing import Annotated

from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.schemas.post import Vote
from app import models
from app.services.auth_service import get_current_user



router = APIRouter(
    prefix="/vote",
    tags=["Vote"]
)

db_session = Annotated[Session, Depends(get_session)]

@router.post("/", status_code=status.HTTP_201_CREATED)
def vote(vote: Vote, session: db_session, current_user: models.Users = Depends(get_current_user)):
    post = session.get(models.Posts, vote.post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    vote_query = session.query(models.Votes).filter(
        models.Votes.post_id == vote.post_id,
        models.Votes.user_id == current_user.id
    )
    found_vote = vote_query.first()

    if vote.dir == 1:
        if found_vote:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User has already voted on this post")
        new_vote = models.Votes(post_id=vote.post_id, user_id=current_user.id)
        session.add(new_vote)
        session.commit()
        return {"message": "Vote added"}
    else:
        if not found_vote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vote does not exist")
        vote_query.delete()
        session.commit()
        return {"message": "Vote removed"}