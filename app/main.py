from fastapi import FastAPI
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db, ping_db

app = FastAPI()

@app.get("/")
def health():
    return {"corriendo con exito Andes Airlines API"}

@app.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    try:
        ping_db()
        return {"ping a BD": True}
    except Exception:
        return {"code": 400, "errors": "could not connect to db"}
