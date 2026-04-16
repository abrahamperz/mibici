from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Station, Reservation
from app.schemas import ReservationResponse

router = APIRouter(tags=["reservations"])


@router.post(
    "/stations/{station_id}/reserve",
    response_model=ReservationResponse,
    status_code=201,
)
async def reserve_bike(station_id: int, db: AsyncSession = Depends(get_db)):
    """Reserve a bike using pg_advisory_xact_lock for concurrency safety."""
    await db.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": station_id})

    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(404, "Station not found")
    if station.available_bikes <= 0:
        raise HTTPException(409, "No bikes available")

    station.available_bikes -= 1

    reservation = Reservation(station_id=station_id, status="active")
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation


@router.post(
    "/stations/{station_id}/return",
    response_model=ReservationResponse,
    status_code=200,
)
async def return_bike(station_id: int, db: AsyncSession = Depends(get_db)):
    """Return a bike using pg_advisory_xact_lock for concurrency safety."""
    await db.execute(text("SELECT pg_advisory_xact_lock(:id)"), {"id": station_id})

    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(404, "Station not found")
    if station.available_bikes >= station.total_slots:
        raise HTTPException(409, "Station is full")

    station.available_bikes += 1

    # Close the oldest active reservation for this station
    result = await db.execute(
        text(
            "UPDATE reservations SET status = 'returned', returned_at = now() "
            "WHERE id = (SELECT id FROM reservations WHERE station_id = :sid AND status = 'active' "
            "ORDER BY reserved_at ASC LIMIT 1) RETURNING *"
        ),
        {"sid": station_id},
    )
    row = result.first()
    await db.commit()

    if row:
        return ReservationResponse(
            id=row.id,
            station_id=row.station_id,
            reserved_at=row.reserved_at,
            returned_at=row.returned_at,
            status=row.status,
        )
    # No active reservation to close, but bike returned
    reservation = Reservation(station_id=station_id, status="returned")
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation
