# from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# from app.core.config import (
#     MAIL_USERNAME,
#     MAIL_PASSWORD,
#     MAIL_FROM,
#     MAIL_PORT,
#     MAIL_SERVER,
# )
import smtplib

from email.mime.text import MIMEText

from app.models.email_setting import EmailSetting
from app.core.encryption import decrypt_password


# conf = ConnectionConfig(
#     MAIL_USERNAME=MAIL_USERNAME,
#     MAIL_PASSWORD=MAIL_PASSWORD,
#     MAIL_FROM=MAIL_FROM,
#     MAIL_PORT=MAIL_PORT,
#     MAIL_SERVER=MAIL_SERVER,
#     MAIL_STARTTLS=True,
#     MAIL_SSL_TLS=False,
#     USE_CREDENTIALS=True,
#     VALIDATE_CERTS=True
# )


# =========================
# RESET PASSWORD EMAIL
# =========================
async def send_reset_email(db, email: str, token: str):
    reset_link = f"http://localhost:8080/reset-password?token={token}"

    body = f"""
    Click the link below to reset your password:

    {reset_link}

    This link will expire in 10 minutes.
    """

    send_custom_email(
        db=db,
        to_email=email,
        subject="Password Reset",
        body=body
    )


# =========================
# EMAIL VERIFICATION
# =========================
async def send_verification_email(db, email: str, token: str):
    verification_link = f"http://localhost:8080/verify-email?token={token}"

    body = f"""
    <p>Hello,</p>

    <p>Please verify your email by clicking
    the button below:</p>

    <a href="{verification_link}"
    style="background:#2563eb;
    color:white;
    padding:10px 16px;
    text-decoration:none;
    border-radius:6px;
    display:inline-block;">
    Verify Email
    </a>

    <p>Or copy this link:</p>

    <p>{verification_link}</p>
    """

    send_custom_email(
        db=db,
        to_email=email,
        subject="FPT Assistant Email Verification",
        body=body,
        is_html=True
    )


def send_custom_email(db, to_email: str, subject: str, body: str, is_html: bool = False):
    setting = get_active_email_setting(db)

    password = decrypt_password(
        setting.encrypted_password
    )
    print(repr(password))

    subtype = "html" if is_html else "plain"

    msg = MIMEText(
        body,
        subtype,
        "utf-8"
    )

    msg["Subject"] = subject
    if setting.sender_name:
        msg["From"] = (
            f"{setting.sender_name} "
            f"<{setting.sender_email}>"
        )
    else:
        msg["From"] = setting.sender_email
    msg["To"] = to_email

    server = smtplib.SMTP(
        setting.smtp_server,
        setting.smtp_port
    )

    try:

        if setting.use_tls:
            server.starttls()

        print("=" * 50)
        print("SMTP:", setting.smtp_server)
        print("PORT:", setting.smtp_port)
        print("EMAIL:", setting.sender_email)
        print("PASSWORD:", password)
        print("=" * 50)

        server.login(
            setting.sender_email,
            password
        )

        server.send_message(msg)

    finally:
        server.quit()


def get_active_email_setting(db):
    setting = (
        db.query(EmailSetting)
        .filter(
            EmailSetting.is_active == True
        )
        .first()
    )

    if not setting:
        raise Exception(
            "SMTP configuration not found"
        )

    return setting