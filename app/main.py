from app.db.models.user import user  # 确保 User 模型被加载
from app.db.base import Base
from app.db.session import engine
from fastapi import FastAPI
from app.api.v1.user.user import router as user_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# 允许跨域请求
origins = [
    "http://127.0.0.1:5500",  # 前端地址
    "http://localhost:5500",
    "https://growing-stacia-lok3wetc-6d9121fc.koyeb.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 开发/验证阶段用 *
    allow_credentials=True,
    allow_methods=["*"],         # 允许所有方法 GET, POST...
    allow_headers=["*"],         # 允许所有请求头
)

app.include_router(user_router)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)