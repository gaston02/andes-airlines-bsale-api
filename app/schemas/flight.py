from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

class Passenger(CamelModel):
    passenger_id: int
    dni: str = Field(min_length=1)
    name: str = Field(min_length=1)
    age: int = Field(ge=0)
    country: str = Field(min_length=1)
    boarding_pass_id: int
    purchase_id: int
    seat_type_id: int
    seat_id: Optional[int] = None

class FlightData(CamelModel):
    flight_id: int
    takeoff_date_time: int
    takeoff_airport: str
    landing_date_time: int
    landing_airport: str
    airplane_id: int
    passengers: List[Passenger]

class ApiSuccess(CamelModel):
    code: int = 200
    data: FlightData
