from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession
from app.models import Base
from app.config import settings,normalize_database_url
engine=create_async_engine(normalize_database_url(settings.database_url),pool_pre_ping=True)
Session=async_sessionmaker(engine,expire_on_commit=False)
async def get_db():
 async with Session() as session: yield session
