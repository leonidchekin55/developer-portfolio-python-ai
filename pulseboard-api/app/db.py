from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

database_url=settings.database_url
if database_url.startswith("postgres://"):
    database_url=database_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif database_url.startswith("postgresql://"):
    database_url=database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
engine=create_async_engine(database_url, pool_pre_ping=True)
Session=async_sessionmaker(engine, expire_on_commit=False)
async def get_db():
    async with Session() as session:
        yield session
