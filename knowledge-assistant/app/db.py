from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.models import Base
from app.config import settings,normalize_database_url
database_url = normalize_database_url(settings.database_url)
engine_options = {"pool_pre_ping": True}
if database_url.startswith("postgresql+asyncpg://"):
    # Keep free/shared PostgreSQL pool usage small and recycle idle connections.
    engine_options.update(pool_size=3, max_overflow=0, pool_recycle=1800)
engine=create_async_engine(database_url, **engine_options)
Session=async_sessionmaker(engine,expire_on_commit=False)
async def get_db():
 async with Session() as session: yield session
