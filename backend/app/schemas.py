from datetime import datetime

from pydantic import BaseModel


class StationCreate(BaseModel):
    name: str
    location: str | None = None
    longitude: float
    latitude: float
    total_slots: int
    available_bikes: int = 0
    is_active: bool = True


class StationUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    total_slots: int | None = None
    available_bikes: int | None = None
    is_active: bool | None = None


class StationResponse(BaseModel):
    id: int
    name: str
    location: str | None
    longitude: float
    latitude: float
    total_slots: int
    available_bikes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StationNearestResponse(StationResponse):
    distance_m: float


class ReservationResponse(BaseModel):
    id: int
    station_id: int
    reserved_at: datetime
    returned_at: datetime | None
    status: str

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str
    db: str
