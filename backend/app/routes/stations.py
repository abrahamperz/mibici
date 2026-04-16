from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geography
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_X, ST_Y, ST_DWithin, ST_Distance
from sqlalchemy import select, func, cast, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Station
from app.schemas import StationCreate, StationUpdate, StationResponse, StationNearestResponse

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("/nearest", response_model=list[StationNearestResponse])
async def nearest_stations(
    lon: float = Query(..., ge=-180, le=180),
    lat: float = Query(..., ge=-90, le=90),
    k: int = Query(5, ge=1, le=10000),
    radius_m: float | None = Query(None, ge=0),
    real_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """KNN spatial search using PostGIS GiST index (<-> operator)."""
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)

    geog_geom = cast(Station.geom, Geography)
    geog_point = cast(point, Geography)

    query = (
        select(
            Station,
            ST_X(Station.geom).label("longitude"),
            ST_Y(Station.geom).label("latitude"),
            ST_Distance(geog_geom, geog_point).label("distance_m"),
        )
        .order_by(Station.geom.distance_centroid(point))
        .limit(k)
    )

    if radius_m is not None:
        query = query.where(ST_DWithin(geog_geom, geog_point, radius_m))

    if real_only:
        query = query.where(Station.name.not_like("Synthetic%"))

    result = await db.execute(query)
    rows = result.all()

    return [
        StationNearestResponse(
            id=row.Station.id,
            name=row.Station.name,
            location=row.Station.location,
            longitude=row.longitude,
            latitude=row.latitude,
            total_slots=row.Station.total_slots,
            available_bikes=row.Station.available_bikes,
            is_active=row.Station.is_active,
            created_at=row.Station.created_at,
            updated_at=row.Station.updated_at,
            distance_m=row.distance_m,
        )
        for row in rows
    ]


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(station_id: int, db: AsyncSession = Depends(get_db)):
    query = select(
        Station,
        ST_X(Station.geom).label("longitude"),
        ST_Y(Station.geom).label("latitude"),
    ).where(Station.id == station_id)
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(404, "Station not found")
    return StationResponse(
        id=row.Station.id,
        name=row.Station.name,
        location=row.Station.location,
        longitude=row.longitude,
        latitude=row.latitude,
        total_slots=row.Station.total_slots,
        available_bikes=row.Station.available_bikes,
        is_active=row.Station.is_active,
        created_at=row.Station.created_at,
        updated_at=row.Station.updated_at,
    )


@router.post("", response_model=StationResponse, status_code=201)
async def create_station(data: StationCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate by name or by station code (e.g. "(ZPN-067)")
    existing = await db.execute(select(Station).where(Station.name == data.name))
    if existing.scalars().first():
        raise HTTPException(409, "Ya existe una estacion con ese nombre")

    if data.name.startswith("("):
        code = data.name.split(")")[0] + ")"
        existing_code = await db.execute(
            select(Station).where(Station.name.like(f"{code}%"))
        )
        if existing_code.scalars().first():
            raise HTTPException(409, f"Ya existe una estacion con el codigo {code}")

    station = Station(
        name=data.name,
        location=data.location,
        geom=WKTElement(f"POINT({data.longitude} {data.latitude})", srid=4326),
        total_slots=data.total_slots,
        available_bikes=data.available_bikes,
        is_active=data.is_active,
    )
    db.add(station)
    await db.commit()
    await db.refresh(station)

    query = select(
        Station,
        ST_X(Station.geom).label("longitude"),
        ST_Y(Station.geom).label("latitude"),
    ).where(Station.id == station.id)
    result = await db.execute(query)
    row = result.first()
    return StationResponse(
        id=row.Station.id,
        name=row.Station.name,
        location=row.Station.location,
        longitude=row.longitude,
        latitude=row.latitude,
        total_slots=row.Station.total_slots,
        available_bikes=row.Station.available_bikes,
        is_active=row.Station.is_active,
        created_at=row.Station.created_at,
        updated_at=row.Station.updated_at,
    )


@router.put("/{station_id}", response_model=StationResponse)
async def update_station(
    station_id: int, data: StationUpdate, db: AsyncSession = Depends(get_db)
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(404, "Station not found")
    if data.name is not None:
        station.name = data.name
    if data.location is not None:
        station.location = data.location
    if data.longitude is not None and data.latitude is not None:
        station.geom = WKTElement(
            f"POINT({data.longitude} {data.latitude})", srid=4326
        )
    if data.total_slots is not None:
        station.total_slots = data.total_slots
    if data.available_bikes is not None:
        station.available_bikes = data.available_bikes
    if data.is_active is not None:
        station.is_active = data.is_active
    await db.commit()
    await db.refresh(station)

    query = select(
        Station,
        ST_X(Station.geom).label("longitude"),
        ST_Y(Station.geom).label("latitude"),
    ).where(Station.id == station.id)
    result = await db.execute(query)
    row = result.first()
    return StationResponse(
        id=row.Station.id,
        name=row.Station.name,
        location=row.Station.location,
        longitude=row.longitude,
        latitude=row.latitude,
        total_slots=row.Station.total_slots,
        available_bikes=row.Station.available_bikes,
        is_active=row.Station.is_active,
        created_at=row.Station.created_at,
        updated_at=row.Station.updated_at,
    )


@router.delete("/{station_id}", status_code=204)
async def delete_station(station_id: int, db: AsyncSession = Depends(get_db)):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(404, "Station not found")
    # Delete associated reservations first
    await db.execute(
        text("DELETE FROM reservations WHERE station_id = :sid"),
        {"sid": station_id},
    )
    await db.delete(station)
    await db.commit()
