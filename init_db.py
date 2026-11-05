import asyncio
from app.database import engine, Base
from app.models import User, Trip

async def init_models():
    print("正在连接数据库并尝试建表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建成功！")

if __name__ == "__main__":
    asyncio.run(init_models())