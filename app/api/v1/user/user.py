from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user.user import UserCreate, UserOut, ResetPassword
from app.crud.user.user import create_user, get_user_by_email, authenticate_user, update_user_password
from app.db.session import get_db
from app.core.security import create_access_token, create_password_reset_token, verify_password_reset_token
from app.tasks.email import send_email
from app.core.security import create_access_token, create_refresh_token
from app.db.models.user.reset_token import PasswordResetToken
from datetime import datetime
from sqlalchemy import select
from datetime import timedelta


router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=UserOut, status_code=201)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_user(db, user.email, user.password)
    return new_user

@router.post("/login")
async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
    authenticated_user = await authenticate_user(db, user.email, user.password)
    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # 生成 token
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})  # ← 这里必须生成

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # 生成 token 并设置过期时间
    reset_token = create_password_reset_token({"sub": str(user.id)})
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # 存储 token
    token_obj = PasswordResetToken(
        token=reset_token,
        user_id=str(user.id),
        expires_at=expires_at
    )
    db.add(token_obj)
    await db.commit()

    frontend_base = "https://react-test-tan-eight.vercel.app"
    reset_link = f"{frontend_base}/reset_password.html?token={reset_token}"

    subject = "Password Reset Request"
    body = f"""
Hi,

您请求了密码重置。请在10分钟内点击下面链接完成操作：
{reset_link}

如果超过10分钟未使用，链接将失效，需要重新发起重置请求。

如果不是你本人操作，请忽略本邮件。
"""
    await send_email(to_email=email, subject=subject, body=body)

    return {"msg": f"Password reset link sent to {email}", "test_token": reset_token}


@router.post("/reset-password")
async def reset_password(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    # 查询 token
    result = await db.execute(select(PasswordResetToken).where(PasswordResetToken.token == data.token))
    token_obj = result.scalars().first()
    if not token_obj:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    # 已使用
    if token_obj.used:
        raise HTTPException(status_code=400, detail="Token already used")
    
    # 超过10分钟
    if datetime.utcnow() > token_obj.expires_at:
        raise HTTPException(status_code=400, detail="Token expired")
    
    # 尝试次数
    if token_obj.attempt_count >= 3:
        raise HTTPException(status_code=400, detail="Maximum attempts exceeded")
    
    # 尝试次数 +1
    token_obj.attempt_count += 1
    db.add(token_obj)
    await db.commit()

    # 重置密码
    updated_user = await update_user_password(db, token_obj.user_id, data.new_password)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 成功则立即失效
    token_obj.used = True
    db.add(token_obj)
    await db.commit()

    return {"msg": "Password has been reset successfully"}
