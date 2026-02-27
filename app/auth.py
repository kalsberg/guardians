from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel


class User(BaseModel):
    username: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    return secret


def _users() -> Dict[str, Dict[str, str]]:
    raw = os.getenv("AUTH_USERS_JSON")
    if not raw:
        raise RuntimeError("AUTH_USERS_JSON is not configured")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("AUTH_USERS_JSON must be valid JSON") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError("AUTH_USERS_JSON must be an object keyed by username")

    users: Dict[str, Dict[str, str]] = {}
    for username, value in parsed.items():
        if not isinstance(value, dict):
            raise RuntimeError("Each AUTH_USERS_JSON user must be an object")

        password = value.get("password")
        role = value.get("role")
        if not password or not role:
            raise RuntimeError("Each AUTH_USERS_JSON user needs password and role")

        users[username] = {"password": str(password), "role": str(role)}

    return users


def authenticate_user(username: str, password: str) -> Optional[User]:
    record = _users().get(username)
    if record is None or record["password"] != password:
        return None
    return User(username=username, role=record["role"])


def create_access_token(user: User, expires_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": user.username,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise credentials_error from exc

    username = payload.get("sub")
    role = payload.get("role")
    if not username or not role:
        raise credentials_error

    if username not in _users():
        raise credentials_error

    return User(username=username, role=role)


def is_admin(user: User) -> bool:
    return user.role == "admin"
