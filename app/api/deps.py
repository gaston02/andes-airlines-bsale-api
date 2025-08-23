from fastapi import Depends
from app.repositories.interfaces import IFlightRepository, ISeatRepository
from app.repositories.flights import FlightRepository,SeatRepository
from app.services.flight_service import FlightService

def get_flight_repository() -> IFlightRepository:
    return FlightRepository()

def get_seat_repository() -> ISeatRepository:
    return SeatRepository()


def get_flight_service_seat(
    flight_repo: IFlightRepository = Depends(get_flight_repository),
    seat_repo: ISeatRepository     = Depends(get_seat_repository),
) -> FlightService:
    return FlightService(flight_repo, seat_repo)

def get_flight_service(repo: IFlightRepository = Depends(get_flight_repository)) -> FlightService:
    return FlightService(repo)
