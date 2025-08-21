from sqlalchemy import text

GET_FLIGHT_WITH_PAX = text("""
SELECT
  f.id              AS flight_id,
  f.takeoff_date_time,
  f.landing_date_time,
  f.takeoff_airport,
  f.landing_airport,
  f.airplane_id,
  p.id              AS passenger_id,
  p.dni,
  p.name,
  p.age,
  p.country,
  bp.id             AS boarding_pass_id,
  bp.purchase_id,
  bp.seat_type_id,
  bp.seat_id
FROM flight f
JOIN boarding_pass bp ON bp.flight_id = f.id
JOIN passenger      p ON p.id = bp.passenger_id
WHERE f.id = :flight_id
ORDER BY bp.purchase_id, p.id
""")

def fetch_flight_with_passengers(db, flight_id: int):
    return db.execute(GET_FLIGHT_WITH_PAX, {"flight_id": flight_id}).mappings().all()
