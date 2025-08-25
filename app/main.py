from fastapi import FastAPI
from app.api.routers.flights import flights_router

app = FastAPI(title="Andes Airlines API", version="0.1.0")

@app.get("/", include_in_schema=False)
def root():
    return {"message": "Andes Airlines API corriendo con éxito"}

app.include_router(flights_router)
