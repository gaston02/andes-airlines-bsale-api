from typing import Mapping, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from .interfaces import IFlightRepository

GET_FLIGHT_WITH_PAX = text("""
SELECT
  f.flight_id            AS flight_id,
  f.takeoff_date_time,
  f.landing_date_time,
  f.takeoff_airport,
  f.landing_airport,
  f.airplane_id,
  p.passenger_id         AS passenger_id,
  p.dni,
  p.name,
  p.age,
  p.country,
  bp.boarding_pass_id    AS boarding_pass_id,
  bp.purchase_id,
  bp.seat_type_id,
  bp.seat_id
FROM flight f
JOIN boarding_pass bp ON bp.flight_id    = f.flight_id
JOIN passenger      p  ON p.passenger_id = bp.passenger_id
WHERE f.flight_id = :flight_id
ORDER BY bp.purchase_id, p.passenger_id
""")

class FlightRepository(IFlightRepository):
    def fetch_flight_with_passengers(self, db: Session, flight_id: int) -> List[Mapping[str, Any]]:
        return db.execute(GET_FLIGHT_WITH_PAX, {"flight_id": flight_id}).mappings().all()
