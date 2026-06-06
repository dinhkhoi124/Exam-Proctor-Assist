from pydantic import BaseModel


class EmailSettingCreate(BaseModel):

    smtp_server: str

    smtp_port: int

    sender_email: str

    sender_name: str

    app_password: str

    use_tls: bool = True

class TestEmailRequest(BaseModel):
    email: str