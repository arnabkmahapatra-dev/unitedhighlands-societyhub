"""Database engine, session factory and declarative base."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _normalize_db_url(url: str) -> str:
    # Some providers (Neon/Render/Heroku) hand out "postgres://"; SQLAlchemy
    # needs the "postgresql://" scheme (with the psycopg2 driver).
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _normalize_db_url(settings.DATABASE_URL)

connect_args = {}
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    # Needed so SQLite can be used across FastAPI's threadpool.
    connect_args = {"check_same_thread": False}
else:
    # Recycle connections so managed Postgres (Neon) doesn't drop idle ones.
    engine_kwargs = {"pool_pre_ping": True, "pool_recycle": 300}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args, future=True, **engine_kwargs
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
