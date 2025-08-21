from typing import Protocol, Mapping, Any, List
from sqlalchemy.orm import Session

class IFlightRepository(Protocol):
    def fetch_flight_with_passengers(self, db: Session, flight_id: int) -> List[Mapping[str, Any]]:
        ...
