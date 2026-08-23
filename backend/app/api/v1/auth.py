
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RegisterRequest,
    ResendVerificationRequest
)

from app.services.auth_service import (
    register_user,
    get_user_by_email,
    hash_password,
    create_reset_token,
    verify_email_token,
    login_user,
    create_verification_token,
    get_current_user_from_token,
    invalidate_user_sessions,
    verify_reset_token
)

from app.core.websocket import manager

from app.models.user import User

from app.services.email_service import send_reset_email, send_verification_email
from app.services.logging_service import log_user_activity
from app.db.deps import get_db
from app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])

RESEND_VERIFICATION_MESSAGE = (
    "If the account exists and is not verified, a verification email has been sent."
)
RESEND_VERIFICATION_RATE_LIMIT_SECONDS = 60
_resend_verification_attempts = {}


# =========================
# PASSWORD VALIDATION
# =========================

def validate_password(password: str):
    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )


def enforce_resend_verification_rate_limit(email: str):
    normalized_email = email.lower()
    now = datetime.now(timezone.utc)
    last_attempt = _resend_verification_attempts.get(normalized_email)

    if last_attempt:
        elapsed = now - last_attempt
        if elapsed < timedelta(seconds=RESEND_VERIFICATION_RATE_LIMIT_SECONDS):
            raise HTTPException(
                status_code=429,
                detail="Please wait before requesting another verification email."
            )

    _resend_verification_attempts[normalized_email] = now


# =========================
# REGISTER
# =========================
@router.post("/register", response_model=MessageResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db), req: Request = None):

    ip = req.client.host if req else "Unknown"

    validate_password(request.password)

    if request.password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    try:

        # Create user
        user = register_user(
            db,
            username=request.username,
            email=request.email,
            password=request.password
        )

        # Create verification token
        token = create_verification_token(db, user)

        # Send verification email
        await send_verification_email(db, user.email, token)

        logger.info(f"REGISTER SUCCESS - {request.email} - IP: {ip}")
        await manager.broadcast({"type": "STATS_UPDATED"})

        return MessageResponse(
            message="Registration successful. Please check your email to verify your account."
        )

    except HTTPException as e:
        logger.warning(
            f"REGISTER FAILED - {request.email} - "
            f"Reason: {e.detail} - IP: {ip}"
        )
        raise e

    except Exception as e:
        logger.error(
            f"REGISTER ERROR - {request.email} - "
            f"Unexpected: {str(e)} - IP: {ip}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


# =========================
# VERIFY EMAIL
# =========================
@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):

    user, error = verify_email_token(db, token)

    if error == "invalid":
        return JSONResponse(
            status_code=400,
            content={
                "message": "Verification link is no longer valid. Please use the latest verification email."
            }
        )

    if error == "expired":
        return JSONResponse(
            status_code=400,
            content={"message": "Verification link expired"}
        )

    return {
        "message": "Email verified successfully",
        "username": user.username,
        "email": user.email
    }

# =========================
# RESEND VERIFICATION EMAIL
# =========================
@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db),
    req: Request = None
):
    ip = req.client.host if req else "Unknown"

    enforce_resend_verification_rate_limit(request.email)

    user = get_user_by_email(db, request.email)

    if user and user.is_active and not user.is_deleted and not user.is_verified:
        token = create_verification_token(db, user)
        await send_verification_email(db,user.email, token)
        logger.info(f"VERIFICATION EMAIL RESENT - {user.email} - IP: {ip}")

    return MessageResponse(message=RESEND_VERIFICATION_MESSAGE)

# =========================
# LOGIN
# =========================
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db), req: Request = None):

    ip = req.client.host if req else "Unknown"

    try:
        token, user = login_user(db, request.identifier, request.password)
        
        user.last_active = datetime.now(timezone.utc)
        db.commit()

        logger.info(f"LOGIN SUCCESS - {request.identifier} - IP: {ip}")
        log_user_activity(db, user.id, "login")
        await manager.broadcast({"type": "STATS_UPDATED"})

        user_data = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role
        } if user else None

        return LoginResponse(access_token=token, user=user_data)

    except HTTPException as e:
        logger.warning(
            f"LOGIN FAILED - {request.identifier} - "
            f"Reason: {e.detail} - IP: {ip}"
        )

        if (
            isinstance(e.detail, dict)
            and e.detail.get("error") == "EMAIL_NOT_VERIFIED"
        ):
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail
            )

        raise e

    except Exception as e:
        logger.error(
            f"LOGIN ERROR - {request.identifier} - "
            f"{str(e)} - IP: {ip}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


# =========================
# LOGOUT
# =========================
@router.post("/logout", response_model=MessageResponse)
async def logout(req: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user_from_token)):

    ip = req.client.host
    
    current_user.last_active = None
    invalidate_user_sessions(current_user)
    db.commit()

    logger.info(f"LOGOUT - User {current_user.email} - IP: {ip}")
    log_user_activity(db, current_user.id, "logout")
    await manager.broadcast({"type": "STATS_UPDATED"})

    return MessageResponse(message="Logout successful")


# =========================
# FORGOT PASSWORD
# =========================
@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    req: Request = None
):
    ip = req.client.host if req else "Unknown"

    user = get_user_by_email(db, request.email)

    # Email không tồn tại
    if not user:
        logger.warning(f"RESET FAILED - Email not found: {request.email} - IP: {ip}")
        raise HTTPException(
            status_code=404,
            detail="This email is not registered."
        )

    # Email tồn tại → gửi reset mail
    if user.is_deleted or not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đã bị khóa hoặc đang trong thời gian chờ xóa.",
        )

    token = create_reset_token(db, user)
    await send_reset_email(db=db, email=user.email, token=token)

    logger.info(f"RESET EMAIL SENT - {request.email} - IP: {ip}")

    return MessageResponse(
        message="Password reset link has been sent to your email."
    )


# =========================
# RESET PASSWORD
# =========================
@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    req: Request = None
):
    ip = req.client.host if req else "Unknown"

    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    validate_password(request.new_password)

    user = verify_reset_token(db, request.token)

    if not user:
        logger.warning(f"RESET FAILED - Invalid token - IP: {ip}")
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired token"
        )

    user.password_hash = hash_password(request.new_password)
    user.reset_token = None
    user.token_expiry = None
    user.last_active = None
    invalidate_user_sessions(user)

    db.commit()

    logger.info(f"PASSWORD RESET SUCCESS - {user.email} - IP: {ip}")

    return MessageResponse(message="Password reset successful")
