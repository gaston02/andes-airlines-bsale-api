# app/db.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Carga el .env según ENV
load_dotenv()
ENV = os.getenv("ENV", "local").lower()
load_dotenv(Path(".env.prod" if ENV == "prod" else ".env.local"), override=True)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=4,
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
