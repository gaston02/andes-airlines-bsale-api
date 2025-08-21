from typing import Mapping, Any, List
from sqlalchemy.orm import Session
from app.repositories.interfaces import IFlightRepository

class FlightService:
    def __init__(self, repo: IFlightRepository):
        self.repo = repo

    # Para el endpoint de debug
    def fetch_flight_rows(self, db: Session, flight_id: int) -> List[Mapping[str, Any]]:
        return self.repo.fetch_flight_with_passengers(db, flight_id)

    # Aquí luego agregarás:
    # - método que arma el objeto final (schemas) y aplica reglas:
    #   menores junto a adulto, contigüidad por compra y clase correcta.
