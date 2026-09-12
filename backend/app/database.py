from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from app.config import settings

engine = create_async_engine(
    settings.database_url, echo=settings.debug, connect_args={"check_same_thread": False}
)

# Enable WAL mode and a 5-second busy timeout for every new SQLite connection.
# WAL allows concurrent reads and writes; busy_timeout prevents immediate "database is locked" errors.
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with async_session_maker() as session:
        yield session
