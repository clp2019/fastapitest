from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ✅ 使用 asyncpg 驱动创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,          # 调试时可设 True
    pool_pre_ping=True,  # 检查连接是否可用
    future=True          # 启用 SQLAlchemy 2.0 行为
)

# ✅ 创建异步 SessionLocal
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ✅ FastAPI 依赖
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
