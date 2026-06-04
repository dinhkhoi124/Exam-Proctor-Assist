from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

from app.core.config import (
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_FROM,
    MAIL_PORT,
    MAIL_SERVER,
)


conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


# =========================
# RESET PASSWORD EMAIL
# =========================
async def send_reset_email(email: str, token: str):
    reset_link = f"http://localhost:8080/reset-password?token={token}"

    message = MessageSchema(
        subject="Password Reset",
        recipients=[email],
        body=f"""
Click the link below to reset your password:

{reset_link}

This link will expire in 10 minutes.
""",
        subtype="plain"
    )

    fm = FastMail(conf)
    await fm.send_message(message)


# =========================
# EMAIL VERIFICATION
# =========================
async def send_verification_email(email: str, token: str):
    verification_link = f"http://localhost:8080/verify-email?token={token}"

    message = MessageSchema(
        subject="FPT Assistant Email Verification",
        recipients=[email],
        body=f"""
        <p>Hello,</p>

        <p>Please verify your email by clicking the button below:</p>

        <a href="{verification_link}"
        style="background:#2563eb;color:white;padding:10px 16px;
        text-decoration:none;border-radius:6px;display:inline-block;">
        Verify Email
        </a>

        <p>Or copy this link:</p>

        <p>{verification_link}</p>
        """,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message)
