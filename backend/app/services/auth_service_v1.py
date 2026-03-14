# chưa xác thực gmail

from datetime import datetime, timedelta
import secrets
import re

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.core.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    RESET_TOKEN_EXPIRE_MINUTES
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =========================
# PASSWORD
# =========================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# =========================
# EMAIL DOMAIN VALIDATION
# =========================

def validate_fpt_domain(email: str):
    pattern = r"^[a-zA-Z0-9._%+-]+@(fe|fpt)\.edu\.vn$"
    if not re.match(pattern, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email must be @fpt.edu.vn or @fe.edu.vn"
        )


# =========================
# JWT LOGIN TOKEN
# =========================

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


# =========================
# DATABASE HELPERS
# =========================

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


# =========================
# REGISTER (BUSINESS LOGIC)
# =========================

def register_user(db: Session, username: str, email: str, password: str):
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    # Validate domain
    validate_fpt_domain(email)

    # Check email exists
    if get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check username exists
    if get_user_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # Create user
    hashed_password = hash_password(password)

    user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# =========================
# LOGIN
# =========================

def login_user(db: Session, identifier: str, password: str):

    if "@" in identifier:
        user = get_user_by_email(db, identifier)
    else:
        user = get_user_by_username(db, identifier)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    token = create_access_token({"sub": str(user.id)})
    return token


# =========================
# RESET TOKEN (DB-BASED)
# =========================

def create_reset_token(db: Session, user: User):
    token = secrets.token_urlsafe(32)

    expiry = datetime.utcnow() + timedelta(
        minutes=RESET_TOKEN_EXPIRE_MINUTES
    )

    user.reset_token = token
    user.token_expiry = expiry

    db.commit()

    return token


def verify_reset_token(db: Session, token: str):
    user = db.query(User).filter(User.reset_token == token).first()

    if not user:
        return None

    if not user.token_expiry:
        return None

    if datetime.utcnow() > user.token_expiry:
        return None

    return user