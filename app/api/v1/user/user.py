# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.schemas.user.user import UserCreate, UserOut
# from fastapi import Body

# from app.crud.user.user import create_user, get_user_by_email, authenticate_user

# from app.db.session import get_db
# import jwt
# from datetime import datetime, timedelta
# from app.core.config import settings

# SECRET_KEY = settings.SECRET_KEY
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30
# REFRESH_TOKEN_EXPIRE_DAYS = 7

# router = APIRouter(prefix="/users", tags=["users"])

# def create_access_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# def create_refresh_token(data: dict, expires_delta: timedelta = None):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
#     to_encode.update({"exp": expire, "type": "refresh"})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# @router.post("/register", response_model=UserOut, status_code=201)
# async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     existing = await get_user_by_email(db, user.email)
#     if existing:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     new_user = await create_user(db, user.email, user.password)
#     return new_user

# @router.post("/login")
# async def login(user: UserCreate, db: AsyncSession = Depends(get_db)):
#     authenticated_user = await authenticate_user(db, user.email, user.password)
#     if not authenticated_user:
#         raise HTTPException(status_code=401, detail="Invalid email or password")
#     access_token = create_access_token({"sub": user.email})
#     refresh_token = create_refresh_token({"sub": user.email})
#     return {
#         "access_token": access_token,
#         "refresh_token": refresh_token,
#         "token_type": "bearer"
#     }

# @router.post("/forgot-password")
# async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
#     user = await get_user_by_email(db, email)
#     if not user:
#         raise HTTPException(status_code=404, detail="Email not found")
#     # 这里可以发送邮件或返回重置 token
#     return {"msg": f"Password reset link sent to {email}"}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user.user import UserCreate, UserOut, ResetPassword
from app.crud.user.user import create_user, get_user_by_email, authenticate_user, update_user_password
from app.db.session import get_db
from app.core.security import create_access_token, create_password_reset_token, verify_password_reset_token
from app.tasks.email import send_email
from app.core.security import create_access_token, create_refresh_token


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
    
    reset_token = create_password_reset_token({"sub": str(user.id)})

    # 本地前端页面地址
    frontend_base = "http://127.0.0.1:5500"
    reset_link = f"{frontend_base}/reset_password.html?token={reset_token}"

    subject = "Password Reset Request"
    body = f"""
Hi,

点击下面链接重置密码：
{reset_link}

如果不是你本人操作，请忽略本邮件。
"""
    await send_email(to_email=email, subject=subject, body=body)

    # 开发模式返回 token 方便前端测试
    return {"msg": f"Password reset link sent to {email}", "test_token": reset_token}


@router.post("/reset-password")
async def reset_password(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    user_id = verify_password_reset_token(data.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    updated_user = await update_user_password(db, user_id, data.new_password)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"msg": "Password has been reset successfully"}
