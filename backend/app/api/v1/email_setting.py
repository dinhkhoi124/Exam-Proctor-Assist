from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.email_setting import EmailSetting
from app.schemas.email import EmailSettingCreate, TestEmailRequest  
from app.core.encryption import encrypt_password
from app.db.deps import get_db
from app.services.email_service import send_custom_email
from app.services.auth_service import get_current_user_from_token, require_admin
from app.models.user import User

router = APIRouter()

@router.get("/email-settings")
def get_email_setting(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)
    setting = db.query(EmailSetting).first()
    if not setting:
        return {
            "smtp_server": "",
            "smtp_port": 587,
            "sender_email": "",
            "sender_name": "",
            "use_tls": True,
            "is_active": False,
            "has_password": False
        }
    return {
        "smtp_server": setting.smtp_server,
        "smtp_port": setting.smtp_port,
        "sender_email": setting.sender_email,
        "sender_name": setting.sender_name,
        "use_tls": setting.use_tls,
        "is_active": setting.is_active,
        "has_password": bool(setting.encrypted_password)
    }

@router.post("/email-settings")
def save_email_setting(
    payload: EmailSettingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    setting = db.query(
        EmailSetting
    ).first()

    if not setting:
        if not payload.app_password:
            raise HTTPException(
                status_code=400,
                detail="App password is required for the initial SMTP configuration",
            )
        setting = EmailSetting()
        db.add(setting)

    setting.smtp_server = payload.smtp_server
    setting.smtp_port = payload.smtp_port
    setting.sender_email = payload.sender_email
    setting.sender_name = payload.sender_name
    if payload.app_password:
        setting.encrypted_password = encrypt_password(payload.app_password)
    elif not setting.encrypted_password:
        raise HTTPException(
            status_code=400,
            detail="App password is required for the SMTP configuration",
        )
    setting.use_tls = payload.use_tls
    setting.is_active = True  # Make it active upon saving

    db.commit()

    return {
        "message": "saved"
    }

@router.post("/email-settings/test")
def test_email(
    payload: TestEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    require_admin(current_user)

    send_custom_email(
        db=db,
        to_email=payload.email,
        subject="ExamAssist Test Email",
        body="SMTP configuration is working."
    )

    return {
        "message": "Email sent successfully"
    }
