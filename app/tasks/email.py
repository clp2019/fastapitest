from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings

async def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = settings.EMAIL_USER
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_USER,
        password=settings.EMAIL_PASSWORD,
        use_tls=True if settings.EMAIL_PORT == 465 else False,
        start_tls=True if settings.EMAIL_PORT == 587 else False
    )
