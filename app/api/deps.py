from fastapi import Depends
from app.repositories.interfaces import IFlightRepository
from app.repositories.flights import FlightRepository
from app.services.flight_service import FlightService

def get_flight_repository() -> IFlightRepository:
    return FlightRepository()

def get_flight_service(repo: IFlightRepository = Depends(get_flight_repository)) -> FlightService:
    return FlightService(repo)
