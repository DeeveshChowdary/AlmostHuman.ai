from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Ensure we use the asyncpg driver for asynchronous FastAPI execution
# If the connection string is a standard 'postgresql://', upgrade it to 'postgresql+asyncpg://'
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(database_url, echo=False)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    autocommit=False, 
    autoflush=False
)

Base = declarative_base()

async def get_db():
    """
    Dependency to yield an async database session per request.
    """
    async with AsyncSessionLocal() as session:
        yield session
