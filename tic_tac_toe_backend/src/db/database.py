import os
from contextlib import contextmanager
from typing import Generator

from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Determine DB path from environment, fallback to ./tictactoe.db in container root
def _resolve_db_path() -> str:
    # PUBLIC_INTERFACE
    # We accept DB_PATH and TICTACTOE_DB_PATH for flexibility; defaults to ./tictactoe.db
    db_path = (
        os.getenv("DB_PATH")
        or os.getenv("TICTACTOE_DB_PATH")
        or "./tictactoe.db"
    )
    # Expand user and make absolute path relative to backend container root by default
    db_path = os.path.expanduser(db_path)
    return db_path


DB_PATH = _resolve_db_path()

# PUBLIC_INTERFACE
def get_engine(echo: bool = False):
    """Create and cache a SQLModel engine for the SQLite database."""
    global _ENGINE
    if "_ENGINE" not in globals() or _ENGINE is None:
        # Ensure directory exists if path includes a folder
        directory = os.path.dirname(DB_PATH)
        if directory and directory not in (".", ""):
            os.makedirs(directory, exist_ok=True)
        sqlite_url = f"sqlite:///{DB_PATH}"
        _ENGINE = create_engine(sqlite_url, echo=echo, connect_args={"check_same_thread": False})
    return _ENGINE


_ENGINE = None


# PUBLIC_INTERFACE
def init_db(echo: bool = False) -> None:
    """Initialize the database and create all tables."""
    engine = get_engine(echo=echo)
    # Import models to ensure tables are registered before create_all
    import src.db.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


# PUBLIC_INTERFACE
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# PUBLIC_INTERFACE
def get_session() -> Generator[Session, None, None]:
    """Yield a session for FastAPI dependency injection."""
    with session_scope() as s:
        yield s
