from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()
ENV = os.getenv("ENV", "local").lower()
load_dotenv(Path(f".env.{ENV}"), override=True)

def _req(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v
class Settings:
    def __init__(self) -> None:
        self.DB_HOST = _req("DB_HOST")
        self.DB_PORT = int(os.getenv("DB_PORT", "3306"))
        self.DB_USER = _req("DB_USER")
        self.DB_PASS = _req("DB_PASS")
        self.DB_NAME = _req("DB_NAME")
            

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()
