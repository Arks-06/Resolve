"""
Initializes asynchronous and synchronous psycopg connection pools with strict autocommit configurations.
Yields the active database sessions to the FastAPI dependency injection system for isolated request handling.
"""

import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Explicitly load the local .env file before inspecting environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is missing")

# Initialize asynchronous engine with optimized connection pooling parameters
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

async_session_maker = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    """Abstract base class for all relational and vector relational entities."""
    pass

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider for FastAPI route contexts ensuring strict session lifecycle cleanup."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()