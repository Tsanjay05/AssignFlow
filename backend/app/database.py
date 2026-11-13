import datetime
import os
from pathlib import Path
from sqlalchemy import create_engine, event, types
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Stable database location regardless of current working directory
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (BASE_DIR / "assignflow.db").resolve()
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}")

# Create SQLAlchemy engine with SQLite thread handling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Enable SQLite foreign-key enforcement
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base
Base = declarative_base()


class UTCDateTime(types.TypeDecorator):
    """
    Reusable UTC-aware DateTime SQLAlchemy type.
    - Accepts timezone-aware timestamps.
    - Rejects naive timestamps for fields requiring timezone-aware input.
    - Normalizes timestamps to UTC before persistence.
    - Restores UTC timezone metadata upon retrieval from SQLite.
    """
    impl = types.DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, datetime.datetime):
                raise ValueError(f"Expected datetime.datetime, got {type(value).__name__}")
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                raise ValueError("Naive datetime is not permitted; timezone-aware datetime is required.")
            return value.astimezone(datetime.timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                return value.replace(tzinfo=datetime.timezone.utc)
            return value.astimezone(datetime.timezone.utc)
        return value


def get_db():
    """Dependency that yields a database session and guarantees closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
