
from fastapi import APIRouter, HTTPException, status, Depends, Request
from sqlalchemy.orm import Session

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RegisterRequest
)

from app.services.auth_service import (
    register_user,
    get_user_by_email,
    hash_password,
    create_reset_token,
    verify_email_token,
    login_user,
    create_verification_token,
    get_current_user_from_token
)

from app.core.websocket import manager

from app.models.user import User

from app.services.email_service import send_reset_email, send_verification_email
from app.db.deps import get_db
from app.core.logger import logger

router = APIRouter(prefix="/auth", tags=["Auth"])


# =========================
# PASSWORD VALIDATION
# =========================

def validate_password(password: str):
    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters"
        )


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
        await send_verification_email(user.email, token)

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

    user = verify_email_token(db, token)

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )

    return {
        "message": "Email verified successfully",
        "username": user.username,
        "email": user.email
    }

# =========================
# LOGIN
# =========================
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db), req: Request = None):

    ip = req.client.host if req else "Unknown"

    try:
        token, user = login_user(db, request.identifier, request.password)
        
        from datetime import datetime
        user.last_active = datetime.utcnow()
        db.commit()

        logger.info(f"LOGIN SUCCESS - {request.identifier} - IP: {ip}")
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
    db.commit()

    logger.info(f"LOGOUT - User {current_user.email} - IP: {ip}")
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
    token = create_reset_token(db, user)
    await send_reset_email(user.email, token)

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

    db.commit()

    logger.info(f"PASSWORD RESET SUCCESS - {user.email} - IP: {ip}")

    return MessageResponse(message="Password reset successful")