import os
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

class ForgotPasswordBody(BaseModel):
    username: str

class ResetPasswordBody(BaseModel):
    token: str
    new_password: str


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

@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordBody, session: Session = Depends(db.get_session_dep)):
    import logging
    log = logging.getLogger("uvicorn.error")

    user = session.exec(select(User).where(User.username == body.username.strip())).first()
    if not user:
        raise HTTPException(404, "User not found")

    token = make_token(user.id, user.username)
    frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_origin}/?token={token}"

    log.info("========== PASSWORD RESET ==========")
    log.info("User: %s  |  Email: %s", user.username, user.email)
    log.info("Reset URL: %s", reset_url)
    log.info("=====================================")

    # If SMTP is configured, send a real email here (future enhancement)
    # For now, always return the reset URL in development mode
    is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    return {
        "message": "Reset link ready — check uvicorn logs or use the dev_reset_url below" if not is_production else "Reset link sent to registered email address",
        "dev_reset_url": None if is_production else reset_url,
    }

@router.post("/reset-password")
def reset_password(body: ResetPasswordBody, session: Session = Depends(db.get_session_dep)):
    from jose import jwt, JWTError
    from routers.auth_utils import SECRET_KEY, ALGORITHM, pwd_context
    
    try:
        payload = jwt.decode(body.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(400, "Invalid or expired token")
        
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
        
    if len(body.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
        
    user.password_hash = pwd_context.hash(body.new_password)
    session.add(user)
    session.commit()
    return {"message": "Password updated successfully"}
