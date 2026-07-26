"""Database engine, session factory and declarative base."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# Arbitrary constant identifying our schema-init advisory lock (Postgres).
_INIT_LOCK_KEY = 4242424242


def _normalize_db_url(url: str) -> str:
    # Some providers (Neon/Render/Heroku) hand out "postgres://"; SQLAlchemy
    # needs the "postgresql://" scheme (with the psycopg2 driver).
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url.startswith(("postgresql://", "sqlite://")):
        scheme = url.split("://", 1)[0] if "://" in url else url
        raise ValueError(
            f"DATABASE_URL has an unsupported scheme: {scheme!r}. "
            "Use a 'postgresql://...' connection string (e.g. from Neon) "
            "or a 'sqlite://...' path."
        )
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


def _create_and_seed() -> None:
    from .seed import run_seed  # local import avoids a circular import

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        _ensure_transaction_columns(conn)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


# Columns added after the first release; create_all won't ALTER existing
# tables, so we add them idempotently here.
_TRANSACTION_ADDED_COLUMNS = [
    ("flat_no", "VARCHAR(30)"),
    ("period_month", "VARCHAR(7)"),
    ("maintenance_amount", "NUMERIC(12, 2)"),
    ("water_bill", "NUMERIC(12, 2)"),
    ("due_advance", "NUMERIC(12, 2)"),
    ("payment_date", "DATE"),
]


def _ensure_transaction_columns(conn) -> None:
    dialect = engine.dialect.name
    if dialect == "postgresql":
        for name, ddl in _TRANSACTION_ADDED_COLUMNS:
            conn.execute(
                text(f"ALTER TABLE transactions ADD COLUMN IF NOT EXISTS {name} {ddl}")
            )
    elif dialect == "sqlite":
        existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(transactions)").fetchall()
        }
        for name, ddl in _TRANSACTION_ADDED_COLUMNS:
            if name not in existing:
                conn.exec_driver_sql(f"ALTER TABLE transactions ADD COLUMN {name} {ddl}")


def init_db() -> None:
    """Create tables and seed data, safely across multiple workers.

    On Postgres, several gunicorn workers boot concurrently and would each run
    ``create_all`` / seeding at the same time, racing on things like
    ``CREATE TYPE userrole ...``. A session-level advisory lock serializes the
    work so exactly one worker initializes while the others wait, then no-op.
    """
    if engine.dialect.name != "postgresql":
        _create_and_seed()
        return

    with engine.connect() as conn:
        # Session-level lock: held on this connection across commits until we
        # explicitly unlock, unlike a transaction-scoped lock.
        conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _INIT_LOCK_KEY})
        conn.commit()
        try:
            _create_and_seed()
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": _INIT_LOCK_KEY})
            conn.commit()
