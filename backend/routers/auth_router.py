from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select
from typing import Optional

import db
from models import User
from routers.auth_utils import pwd_context, make_token, get_current_user_optional

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str
    password: str
    email: str = ""


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterBody, session: Session = Depends(db.get_session_dep)):
    username = body.username.strip()
    if not username:
        raise HTTPException(400, "Username cannot be empty")
    if len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        raise HTTPException(400, "Username already taken")
    user = User(
        username=username,
        email=body.email.strip(),
        password_hash=pwd_context.hash(body.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return TokenOut(
        access_token=make_token(user.id, user.username),
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=TokenOut)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(db.get_session_dep),
):
    user = session.exec(select(User).where(User.username == form.username)).first()
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    return TokenOut(
        access_token=make_token(user.id, user.username),
        user_id=user.id,
        username=user.username,
    )


@router.get("/me")
def me(user: Optional[User] = Depends(get_current_user_optional)):
    if not user:
        raise HTTPException(401, "Not authenticated")
    return {"user_id": user.id, "username": user.username, "email": user.email}
