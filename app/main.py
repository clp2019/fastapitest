# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from app.db.session import Base, db_manager
# from app.api.v1.user.user import router as user_router
# from app.api.v1.fruit import router as fruit_router

# app = FastAPI()

# # CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(user_router)
# app.include_router(fruit_router)

# @app.on_event("startup")
# async def startup():
#     await db_manager.init()
#     async with db_manager.engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

# @app.on_event("shutdown")
# async def shutdown():
#     await db_manager.dispose()


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

import os
import uvicorn

# ==== 初始化应用 ====
app = FastAPI(
    title="Fruit API Service",
    description="基于 FastAPI 的电商后端示例",
    version="1.0.0",
)

# ==== 中间件 ====
# 支持跨域请求（方便 Vercel 前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 部署上线后可改为你的前端域名，如 https://your-frontend.vercel.app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 压缩响应，提高传输效率
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ==== 模拟依赖模块（数据库、Redis、Cloudinary等）====
# 实际项目中你可在 /core 或 /database 文件夹中实现连接
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

@app.on_event("startup")
async def startup_event():
    print("🚀 FastAPI 服务启动中...")
    print(f"📦 数据库连接：{DATABASE_URL}")
    print(f"🔗 Redis 连接：{REDIS_URL}")
    print("✅ 服务初始化完成！")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 服务已关闭")

# ==== 示例路由 ====
@app.get("/")
def root():
    return {"message": "FastAPI 运行中，部署成功！"}

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "message": "Server is healthy"}

@app.get("/api/v1/fruits")
def get_fruits():
    fruits = [
        {"id": 1, "name": "Apple", "price": 3.5},
        {"id": 2, "name": "Banana", "price": 2.0},
        {"id": 3, "name": "Orange", "price": 4.0},
    ]
    return JSONResponse(content={"data": fruits, "count": len(fruits)})

# ==== 可选：挂载静态文件（图片、上传文件） ====
if not os.path.exists("static"):
    os.mkdir("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==== 主程序入口 ====
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
