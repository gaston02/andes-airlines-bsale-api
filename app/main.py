from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, ping_db

app = FastAPI(title="Andes Airlines API", version="0.1.0")

@app.get("/")
def root():
    return {"message": "Andes Airlines API corriendo con éxito"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    try:
        ping_db()
        return {"ok": True}
    except Exception:
        return {"code": 400, "errors": "could not connect to db"}
