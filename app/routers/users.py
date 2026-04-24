from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])
db_session = Annotated[Session, Depends(get_session)]


@router.post("/", status_code=201, response_model=UserResponse)
async def create_user(payload: UserCreate, session: db_session):
    user = await user_service.create_user(payload, session)
    return user


@router.get("/", response_model=List[UserResponse])
async def get_users(session: db_session):
    users = await user_service.get_users(session)
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, session: db_session):
    user = await user_service.get_user(user_id, session)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdate, session: db_session):
    user = await user_service.update_user(user_id, payload, session)
    return user


@router.delete("/{user_id}")
async def delete_user(user_id: int, session: db_session):
    result = await user_service.delete_user(user_id, session)
    return result
