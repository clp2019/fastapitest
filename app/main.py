# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.user.user import router as user_router
from app.api.v1.fruit.fruit import router as fruit_router
from app.db.base import Base
from app.db.session import engine

app = FastAPI(
    title="Fruit API",
    description="A FastAPI + PostgreSQL + Cloudinary service",
    version="1.0.0"
)

# ---------------------------
# ✅ CORS 配置
# ---------------------------
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://react-test-tan-eight.vercel.app",
    "https://growing-stacia-lok3wetc-6d9121fc.koyeb.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# ✅ 路由注册
# ---------------------------
app.include_router(user_router)
app.include_router(fruit_router)

# ---------------------------
# ✅ 健康检查
# ---------------------------
@app.get("/")
async def root():
    return {"status": "ok", "service": "fruit-api", "version": "v1"}

# ---------------------------
# ✅ 数据库初始化
# ---------------------------
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables checked/created.")
