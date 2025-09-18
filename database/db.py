from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from logger import db_logger

DATABASE_URL = "sqlite+aiosqlite:///database/bot.db"

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    db_logger.info("Инициализация базы данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        db_logger.info("✅ Таблицы успешно созданы")
