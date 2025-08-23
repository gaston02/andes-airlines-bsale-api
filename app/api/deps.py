from fastapi import Depends
from app.repositories.interfaces import IFlightRepository, ISeatRepository
from app.repositories.flights import FlightRepository,SeatRepository
from app.repositories.test import FlightAuditRepository
from app.services.flight_service import FlightService
from app.services.flight_audit_service import FlightAuditService
from app.repositories.fake_flight_repo import FakeFlightRepo

USE_FAKE_AUDIT_REPO = True

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

def get_audit_repo():
    return FakeFlightRepo() if USE_FAKE_AUDIT_REPO else FlightAuditRepository()

def get_flight_audit_service(repo = Depends(get_audit_repo)) -> FlightAuditService:
    return FlightAuditService(repo)