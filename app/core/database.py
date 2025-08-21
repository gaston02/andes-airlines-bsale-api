from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import settings  # toma DATABASE_URL desde core/config

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # reabre si la conexión murió por inactividad
    pool_recycle=4,       # < 5s del servidor compartido
    pool_size=1,
    max_overflow=0,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ping_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
