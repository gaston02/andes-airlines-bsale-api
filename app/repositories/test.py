# app/repositories/test.py  (nuevo archivo de prueba)

from typing import Mapping, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

# -- NUEVA QUERY: pasajeros + posición del asiento asignado
GET_FLIGHT_WITH_PAX_AND_SEATPOS = text("""
SELECT
  f.flight_id                 AS flight_id,
  f.takeoff_date_time,
  f.landing_date_time,
  f.takeoff_airport,
  f.landing_airport,
  f.airplane_id,
  p.passenger_id              AS passenger_id,
  p.dni,
  p.name,
  p.age,
  p.country,
  bp.boarding_pass_id         AS boarding_pass_id,
  bp.purchase_id,
  bp.seat_type_id,
  bp.seat_id,
  s.seat_row                  AS assigned_seat_row,
  s.seat_column               AS assigned_seat_column
FROM flight f
JOIN boarding_pass bp
  ON bp.flight_id = f.flight_id
JOIN passenger p
  ON p.passenger_id = bp.passenger_id
LEFT JOIN seat s
  ON s.seat_id = bp.seat_id
WHERE f.flight_id = :flight_id
ORDER BY bp.purchase_id, p.passenger_id
""")

# -- Reutilizamos tu query actual de inventario
GET_SEATS_FOR_FLIGHT = text("""
SELECT s.seat_id, s.seat_column, s.seat_row, s.seat_type_id, s.airplane_id
FROM seat s
JOIN flight f ON f.airplane_id = s.airplane_id
WHERE f.flight_id = :flight_id
ORDER BY s.seat_type_id, s.seat_row, s.seat_column
""")

class FlightAuditRepository:
    """Repo minimal para el endpoint de auditoría (no toca tu servicio actual)."""

    def fetch_flight_with_pax_and_seatpos(
        self, db: Session, flight_id: int
    ) -> List[Mapping[str, Any]]:
        return db.execute(
            GET_FLIGHT_WITH_PAX_AND_SEATPOS, {"flight_id": flight_id}
        ).mappings().all()

    def fetch_seats_for_flight(
        self, db: Session, flight_id: int
    ) -> List[Mapping[str, Any]]:
        return db.execute(
            GET_SEATS_FOR_FLIGHT, {"flight_id": flight_id}
        ).mappings().all()
