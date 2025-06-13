from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

BASE_DIR = Path(__file__).resolve().parent

SQLALCHEMY_DATABASE_URL = f"sqlite+aiosqlite:///{BASE_DIR / 'pcb_devices.db'}"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session