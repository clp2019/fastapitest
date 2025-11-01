from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import Base, db_manager
from app.api.v1.user.user import router as user_router
from app.api.v1.fruit import router as fruit_router

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(fruit_router)

@app.on_event("startup")
async def startup():
    await db_manager.init()
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await db_manager.dispose()




