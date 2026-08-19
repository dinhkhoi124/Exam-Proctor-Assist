from datetime import datetime, timedelta, timezone
import secrets
import re

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import User
from app.core.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    RESET_TOKEN_EXPIRE_MINUTES
)
from sqlalchemy import func, update
from app.models.chat_log import ChatLog
from app.db.deps import get_db

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


def normalize_email(email: str) -> str:
    return str(email).strip().lower()


def normalize_username(username: str) -> str:
    return username.strip()


# =========================
# JWT LOGIN TOKEN
# =========================

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def invalidate_user_sessions(user: User) -> None:
    """Invalidate every access token previously issued for this user."""
    user.session_version += 1


def _session_unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


# =========================
# DATABASE HELPERS
# =========================

def get_user_by_username(db: Session, username: str):
    normalized_username = normalize_username(username)
    return db.query(User).filter(
        func.lower(User.username) == normalized_username.lower()
    ).first()


def get_user_by_email(db: Session, email: str):
    normalized_email = normalize_email(email)
    return db.query(User).filter(
        func.lower(User.email) == normalized_email
    ).first()


# =========================
# REGISTER (BUSINESS LOGIC)
# =========================

def register_user(db: Session, username: str, email: str, password: str):
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )

    username = normalize_username(username)
    email = normalize_email(email)

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )

    # Validate domain
    validate_fpt_domain(email)

    # Check email exists
    existing_user = get_user_by_email(db, email)
    if existing_user:
        if existing_user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tài khoản này đang trong thời gian chờ xóa và có thể được khôi phục.",
            )
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
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        ) from exc
    db.refresh(user)

    return user


# =========================
# LOGIN
# =========================

def login_user(db: Session, identifier: str, password: str):
    identifier = identifier.strip()

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
    
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đang trong thời gian chờ xóa.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa. Vui lòng liên hệ quản trị viên.",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "EMAIL_NOT_VERIFIED",
                "message": "Account is not verified",
                "can_resend_verification": True
            }
        )

    session_version = db.execute(
        update(User)
        .where(User.id == user.id)
        .values(session_version=User.session_version + 1)
        .returning(User.session_version)
        .execution_options(synchronize_session=False)
    ).scalar_one()
    token = create_access_token({"sub": str(user.id), "sv": session_version})
    return token, user

def get_current_user(db: Session, user_id: str):
    user = db.query(User).filter(User.id == user_id).first()
    return user

def require_admin(user: User):
    require_roles(user, ["admin"])
    
def require_roles(user: User, allowed_roles: list):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )

def require_manager_or_admin(user: User):
    require_roles(user, ["manager", "admin"])

# =========================
# RESET TOKEN (DB-BASED)
# =========================

def create_reset_token(db: Session, user: User):
    token = secrets.token_urlsafe(32)

    expiry = datetime.now(timezone.utc) + timedelta(
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

    if user.is_deleted or not user.is_active:
        return None

    if datetime.now(timezone.utc) > user.token_expiry:
        return None

    return user


def create_verification_token(db: Session, user: User):
    token = secrets.token_urlsafe(32)

    expiry = datetime.now(timezone.utc) + timedelta(hours=24)

    user.verification_token = token
    user.verification_expiry = expiry

    db.commit()

    return token

def verify_email_token(db: Session, token: str):

    user = db.query(User).filter(
        User.verification_token == token
    ).first()

    if not user:
        return None, "invalid"

    if not user.verification_expiry:
        return None, "expired"

    if user.is_deleted or not user.is_active:
        return None, "invalid"

    if datetime.now(timezone.utc) > user.verification_expiry:
        return None, "expired"

    user.is_verified = True
    user.verification_token = None
    user.verification_expiry = None

    db.commit()

    return user, None

# =========================
# ADMIN STATISTICS
# =========================

def get_total_users(db: Session):
    return db.query(func.count(User.id)).filter(User.is_deleted.is_(False)).scalar()


def get_total_questions(db: Session):
    return db.query(func.count(ChatLog.id)).filter(ChatLog.is_deleted.is_(False)).scalar()


def get_active_users(db: Session):
    return db.query(func.count(User.id)).filter(
        User.is_active.is_(True),
        User.is_deleted.is_(False),
    ).scalar()


def get_user_question_count(db: Session):
    results = (
        db.query(User.username, func.count(ChatLog.id))
        .join(ChatLog, ChatLog.user_id == User.id)
        .group_by(User.username)
        .filter(ChatLog.is_deleted.is_(False), User.is_deleted.is_(False))
        .all()
    )

    return [
        {"username": username, "total_questions": total}
        for username, total in results
    ]

security = HTTPBearer()

def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        token_session_version = payload.get("sv")
    except JWTError as exc:
        raise _session_unauthorized(
            "INVALID_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
        ) from exc

    if not user_id or isinstance(token_session_version, bool) or not isinstance(
        token_session_version, int
    ):
        raise _session_unauthorized(
            "INVALID_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise _session_unauthorized(
            "INVALID_TOKEN", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn."
        )

    if token_session_version != user.session_version:
        raise _session_unauthorized(
            "SESSION_REPLACED",
            "Tài khoản đã được đăng nhập trên một trình duyệt hoặc thiết bị khác.",
        )

    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đang trong thời gian chờ xóa.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa.",
        )

    return user
