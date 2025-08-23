from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, ping_db
from app.api.routers.flights import debug_router, flights_router

app = FastAPI(title="Andes Airlines API", version="0.1.0")

@app.get("/")
def root():
    return {"message": "Andes Airlines API corriendo con éxito"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/db/ping")
def db_ping(_db: Session = Depends(get_db)):
    ping_db()
    return {"ok": True}

app.include_router(debug_router) 
app.include_router(flights_router)
