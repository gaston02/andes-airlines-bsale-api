from typing import Mapping, Any, List, Dict, Set
from sqlalchemy.orm import Session
from app.repositories.interfaces import IFlightRepository, ISeatRepository
from app.schemas.flight import Passenger, FlightData, ApiSuccess

# importar helpers refactorizados
from app.services.seat_rules import (
    Row,
    SeatIndex,
    index_seats,
    assign_minors_next_to_adults,
    assign_group_nearby,
)

class FlightService:
    def __init__(
        self,
        flight_repo: IFlightRepository,
        seat_repo: ISeatRepository | None = None,
    ) -> None:
        self.repo = flight_repo
        self.seats = seat_repo

    # ---------- Públicos (usables desde routers) ----------

    def fetch_flight_rows(self, db: Session, flight_id: int) -> List[Row]:
        return self.repo.fetch_flight_with_passengers(db, flight_id)

    def fetch_seats_for_flight(self, db: Session, flight_id: int) -> List[Row]:
        if self.seats is None:
            raise RuntimeError("Seat repository not provided")
        return self.seats.fetch_seats_for_flight(db, flight_id)

    def build_passengers_response(self, rows: List[Row]) -> ApiSuccess:
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

    def get_flight_passengers_payload(self, db: Session, flight_id: int) -> dict:
        rows = self.fetch_flight_rows(db, flight_id)
        if not rows:
            return {"code": 404, "data": {}}

        mrows: List[Dict[str, Any]] = [dict(r) for r in rows]
        airplane_id = mrows[0]["airplane_id"]

        seats = self.fetch_seats_for_flight(db, flight_id)
        seat_idx: SeatIndex = index_seats(seats)
        occupied: Set[int] = {r["seat_id"] for r in mrows if r["seat_id"] is not None}

        # reglas de negocio (helpers externos)
        assign_minors_next_to_adults(mrows, seat_idx, occupied, airplane_id)
        assign_group_nearby(mrows, seat_idx, occupied, airplane_id)

        return self.build_passengers_response(mrows).model_dump(by_alias=True)
