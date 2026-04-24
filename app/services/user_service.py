from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import EmailStr

from app.db import get_session
from app.models import Users
from app.schemas.user import UserCreate, UserUpdate
from app.utils import hash_password


router = APIRouter()
db_session = Annotated[Session, Depends(get_session)]

async def create_user(payload: UserCreate, session: db_session):
    existing_email = session.exec(select(Users).where(Users.email == payload.email)).first()
    existing_username = session.exec(select(Users).where(Users.username == payload.username)).first()
    if existing_email:
        raise HTTPException(status_code=400, detail=f"User with email {payload.email} already exists")
    if existing_username:
        raise HTTPException(status_code=400, detail=f"User with username {payload.username} already exists")

    user = Users.model_validate(payload)
    user.password = hash_password(user.password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

async def get_users(session: db_session):
    users = session.exec(select(Users)).all()
    return users

async def get_user(user_id: int, session: db_session):
    user = session.get(Users, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    return user

async def get_user_by_email(email: EmailStr, session: db_session):
    user = session.exec(select(Users).where(Users.email == email)).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")
    return user

async def update_user(user_id: int, payload: UserUpdate, session: db_session):
    user = session.get(Users, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    user.sqlmodel_update(payload.model_dump(exclude_unset=True))
    user.password = hash_password(user.password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

async def delete_user(user_id: int, session: db_session):
    user = session.get(Users, user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found")
    session.delete(user)
    session.commit()
    return {"message": f"User with ID {user_id} deleted successfully"}