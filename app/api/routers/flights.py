# app/api/routers/flights.py
from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_flight_service, get_flight_service_seat
from app.services.flight_service import FlightService

debug_router = APIRouter(prefix="/debug/flights", tags=["debug"])
flights_router = APIRouter(prefix="/flights", tags=["flights"])

@debug_router.get("/{flight_id}")
def debug_flight(
    flight_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    svc: FlightService = Depends(get_flight_service),  # solo repo de vuelos
):
    rows = svc.fetch_flight_rows(db, flight_id)
    if not rows:
        return {"code": 404, "data": {}}
    resp = svc.build_passengers_response(rows)
    return resp.model_dump(by_alias=True)

@flights_router.get("/{flight_id}/passengers")
def get_flight_passengers(
    flight_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    svc: FlightService = Depends(get_flight_service_seat),  # vuelos + seats
):
    return svc.get_flight_passengers_payload(db, flight_id)
