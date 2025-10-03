# from sqlalchemy.future import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.db.models.user.user import User
# from app.core.security import hash_password, verify_password

# async def create_user(db: AsyncSession, email: str, password: str) -> User:
#     user = User(email=email, hashed_password=hash_password(password))
#     db.add(user)
#     await db.commit()
#     await db.refresh(user)
#     return user

# async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
#     result = await db.execute(select(User).where(User.email == email))
#     return result.scalars().first()

# async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
#     user = await get_user_by_email(db, email)
#     if user and verify_password(password, user.hashed_password):
#         return user
#     return None


from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.user.user import User
from app.core.security import hash_password, verify_password

async def create_user(db: AsyncSession, email: str, password: str) -> User:
    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user and verify_password(password, user.hashed_password):
        return user
    return None

async def update_user_password(db: AsyncSession, user_id: str, new_password: str):
    user = await db.get(User, user_id)
    if not user:
        return None
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
