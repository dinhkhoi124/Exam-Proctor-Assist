from cryptography.fernet import Fernet
import os

key = os.getenv("EMAIL_ENCRYPT_KEY")

if not key:
    raise Exception(
        "EMAIL_ENCRYPT_KEY missing"
    )

cipher = Fernet(key.encode())

def encrypt_password(password: str):
    return cipher.encrypt(
        password.encode()
    ).decode()

def decrypt_password(token: str):
    return cipher.decrypt(
        token.encode()
    ).decode()