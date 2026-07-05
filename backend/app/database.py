import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

os.makedirs("data", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("uploads", exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/mflux.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# Enable WAL mode for concurrent read/write safety
@event.listens_for(engine, "connect")
def _enable_sqlite_wal(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
