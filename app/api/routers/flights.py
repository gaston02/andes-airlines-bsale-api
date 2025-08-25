from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_flight_service_seat
from app.services.flight_service import FlightService

flights_router = APIRouter(prefix="/flights", tags=["flights"])

@flights_router.get("/{flight_id}/passengers")
def get_flight_passengers(
    flight_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    svc: FlightService = Depends(get_flight_service_seat),
):
    return svc.get_flight_passengers_payload(db, flight_id)