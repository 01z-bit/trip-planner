from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# 这里的账号密码和库名，必须和咱们之前 docker-compose.yml 里写的一模一样
DATABASE_URL = "postgresql+asyncpg://trip:trip_dev@localhost:5432/trip"

# 创建异步引擎
engine = create_async_engine(DATABASE_URL, echo=True)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 创建基类（后面所有的表都要继承它）
Base = declarative_base()

# 获取数据库会话的依赖函数
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session