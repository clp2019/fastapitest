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
    """
    支持逻辑：
    1. 链接有效期 10 分钟；
    2. 失败 3 次后自动失效；
    3. 成功一次后立即失效；
    4. 第一次失败提示剩余次数，第二次仅提示错误，第三次不删除 token；
    """

    # 1️⃣ 验证 token 签名是否合法
    payload = verify_password_reset_token(data.token)
    if not payload:
        raise HTTPException(status_code=400, detail="无效或过期的链接")

    # 2️⃣ 查找数据库中的 token 记录
    token_record = (await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == data.token)
    )).scalar_one_or_none()

    if not token_record:
        raise HTTPException(status_code=400, detail="无效或已失效的链接")

    # 3️⃣ 检查是否过期
    if datetime.utcnow() > token_record.expires_at:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="链接已过期，请重新申请重置")

    # 4️⃣ 检查失败次数
    if token_record.failed_attempts > 3:
        await db.delete(token_record)
        await db.commit()
        raise HTTPException(status_code=400, detail="连续失败次数过多，链接已失效")

    # 5️⃣ 检查密码格式：字母+数字+特殊符号，8-20位
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,20}$"
    if not re.match(pattern, data.new_password):
        token_record.failed_attempts += 1
        await db.commit()

        if token_record.failed_attempts > 3:
            # 达到 3 次 -> 删除 token
            await db.delete(token_record)
            await db.commit()
            raise HTTPException(status_code=400, detail="连续失败 3 次，链接已失效")

        elif token_record.failed_attempts == 1:
            raise HTTPException(
                status_code=400,
                detail="密码格式错误（剩余 2 次机会）"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="密码格式错误（剩余 1 次机会）"
            )

    # 6️⃣ 获取用户
    user_id = payload if isinstance(payload, str) else payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Token 内用户ID无效")

    user = await db.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 7️⃣ 更新密码
    user.hashed_password = hash_password(data.new_password)

    # 8️⃣ 删除 token（重置成功后立即失效）
    await db.delete(token_record)
    await db.commit()

    return {"msg": "密码重置成功！链接已失效，请重新登录。"}
