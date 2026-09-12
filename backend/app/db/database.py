import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, func

from app.paths import DB_PATH, ensure_directories
ensure_directories()
DATABASE_URL = "sqlite+aiosqlite:///" + DB_PATH.as_posix()

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class CameraLog(Base):
    __tablename__ = "camera_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String, index=True)
    event_type = Column(String)  # CONNECT, DISCONNECT, INTERRUPT, RECONNECT
    status = Column(String)
    fps = Column(Float, nullable=True)
    frames_received = Column(Integer, default=0)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
