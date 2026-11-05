from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 👈 必须要有这行
from app.api import auth, trips

app = FastAPI(
    title="多Agent旅游规划系统",
    version="1.0.0"
)

# 👇 必须要有这一段，允许前端 5173 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(trips.router)

@app.get("/")
def read_root():
    return {"message": "Hello, 后端已启动！"}