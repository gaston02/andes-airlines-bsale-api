from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_flight_service
from app.services.flight_service import FlightService

router = APIRouter(prefix="/debug/flights", tags=["debug"])

@router.get("/{flight_id}")
def debug_flight(
    flight_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    svc: FlightService = Depends(get_flight_service),
):
    rows = svc.fetch_flight_rows(db, flight_id)
    if not rows:
        return {"code": 404, "data": {}}
    resp = svc.build_passengers_response(rows)
    return resp.model_dump(by_alias=True)
