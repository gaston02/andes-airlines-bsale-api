from typing import Mapping, Any, List
from sqlalchemy.orm import Session
from app.repositories.interfaces import IFlightRepository
from app.schemas.flight import Passenger, FlightData, ApiSuccess

Row = Mapping[str, Any]

class FlightService:
    def __init__(self, repo: IFlightRepository):
        self.repo = repo

    # Paso 1: obtener filas (una por boarding_pass)
    def fetch_flight_rows(self, db: Session, flight_id: int) -> List[Row]:
        return self.repo.fetch_flight_with_passengers(db, flight_id)

    # Paso 2: transformar filas schemas Pydantic (camelCase al serializar)
    def build_passengers_response(self, rows: List[Row]) -> ApiSuccess:
        """
        rows: lista de mapeos con llaves snake_case según SELECT:
          flight_id, takeoff_date_time, landing_date_time, takeoff_airport, landing_airport, airplane_id,
          passenger_id, dni, name, age, country, boarding_pass_id, purchase_id, seat_type_id, seat_id
        """
        first = rows[0]

        passengers = [
            Passenger(
                passenger_id=r["passenger_id"],
                dni=r["dni"],
                name=r["name"],
                age=r["age"],
                country=r["country"],
                boarding_pass_id=r["boarding_pass_id"],
                purchase_id=r["purchase_id"],
                seat_type_id=r["seat_type_id"],
                seat_id=r["seat_id"],
            )
            for r in rows
        ]

        data = FlightData(
            flight_id=first["flight_id"],
            takeoff_date_time=first["takeoff_date_time"],
            takeoff_airport=first["takeoff_airport"],
            landing_date_time=first["landing_date_time"],
            landing_airport=first["landing_airport"],
            airplane_id=first["airplane_id"],
            passengers=passengers,
        )
        return ApiSuccess(data=data)

    # (Opcional) método fachada para el router “oficial”
    def get_flight_passengers_payload(self, db: Session, flight_id: int) -> dict:
        rows = self.fetch_flight_rows(db, flight_id)
        if not rows:
            return {"code": 404, "data": {}}
        resp = self.build_passengers_response(rows)
        return resp.model_dump(by_alias=True)
