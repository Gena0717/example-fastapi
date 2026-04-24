from typing import Annotated
from fastapi import APIRouter, Depends
from sqlmodel import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.db import get_session
from app.services import auth_service
from app.schemas.user import Token

router = APIRouter(
    prefix="/login",
    tags=["Login"]
)   
db_session = Annotated[Session, Depends(get_session)]

@router.post("/", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: db_session):
  token = await auth_service.login_for_access_token(form_data, session)
  return token

# @router.get("/users/me")
# async def read_users_me(
#     current_user: Annotated[Users, Depends(auth_service.get_current_user)],
# ) -> Users:
#     return await auth_service.read_users_me(current_user)

# @router.get("/users/me/items/")
# async def read_own_items(
#     current_user: Annotated[Users, Depends(auth_service.get_current_user)],
# ):
#     return await auth_service.read_own_items(current_user)