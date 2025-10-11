from fastapi import APIRouter, Depends, HTTPException,status
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
from app.db.models.user.user import User
from app.core.security import hash_password
import re
import uuid

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
    # 防止空 token
    if not data.token or not isinstance(data.token, str) or len(data.token) < 10:
        raise HTTPException(status_code=400, detail="无效或已失效的链接")

    # 验证 token 签名
    payload = verify_password_reset_token(data.token)
    if not payload:
        raise HTTPException(status_code=400, detail="无效或过期的链接")

    token_record = (await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == data.token)
    )).scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=400, detail="无效或已失效的链接")

    # 检查是否过期
    if datetime.utcnow() > token_record.expires_at:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="链接已过期，请重新申请重置")

    # 检查失败次数：允许最多 3 次失败，超过 3 次（>3）则失效
    if token_record.failed_attempts > 3:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="连续失败次数过多，链接已失效")

    # 检查密码格式
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,20}$"
    if not re.match(pattern, data.new_password):
        # 记录一次尝试和一次失败
        token_record.attempt_count = (token_record.attempt_count or 0) + 1
        token_record.failed_attempts = (token_record.failed_attempts or 0) + 1

        # 如果失败次数超过 3 次，则删除 token 并拒绝
        if token_record.failed_attempts > 3:
            await db.delete(token_record)
            await db.commit()
            raise HTTPException(status_code=400, detail="连续失败次数过多，链接已失效")

        await db.commit()
        remaining = max(0, 3 - token_record.failed_attempts)
        raise HTTPException(status_code=400, detail=f"密码格式错误（剩余 {remaining} 次机会）")

    # 获取用户
    user_id = payload if isinstance(payload, str) else payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Token 内用户ID无效")

    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新密码并立即失效
    user.hashed_password = hash_password(data.new_password)
    await db.delete(token_record)
    await db.commit()

    return {"msg": "✅ 密码重置成功！链接已失效。"}
