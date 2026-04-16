"""Seed the database with real MIBICI stations + synthetic expansion to 10K."""

import asyncio
import csv
import io
import random

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db import DATABASE_URL

CSV_URL = "https://www.mibici.net/site/assets/files/1118/nomenclatura_2026_03.csv"

# Guadalajara metro bounding box
LAT_MIN, LAT_MAX = 20.55, 20.75
LON_MIN, LON_MAX = -103.45, -103.25

TARGET_STATIONS = 10_000


async def download_csv() -> list[dict] | None:
    """Download and parse the real MIBICI station CSV."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(CSV_URL)
            resp.raise_for_status()

        content = resp.content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(content))
        rows = []
        for row in reader:
            try:
                rows.append(
                    {
                        "id": int(row["id"]),
                        "name": row["name"].strip(),
                        "location": row.get("location", "").strip(),
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "is_active": row.get("status", "IN_SERVICE").strip() == "IN_SERVICE",
                    }
                )
            except (KeyError, ValueError):
                continue
        print(f"Downloaded {len(rows)} real stations from MIBICI")
        return rows
    except Exception as e:
        print(f"CSV download failed ({e}), using all-synthetic data")
        return None


def generate_synthetic(start_id: int, count: int) -> list[dict]:
    """Generate synthetic stations within Guadalajara bbox."""
    stations = []
    for i in range(count):
        stations.append(
            {
                "id": start_id + i,
                "name": f"Synthetic Station {start_id + i}",
                "location": "Guadalajara",
                "latitude": random.uniform(LAT_MIN, LAT_MAX),
                "longitude": random.uniform(LON_MIN, LON_MAX),
                "is_active": True,
            }
        )
    return stations


async def seed():
    engine = create_async_engine(DATABASE_URL, pool_size=5)
    session_factory = async_sessionmaker(engine, class_=AsyncSession)

    async with session_factory() as session:
        await session.execute(text("TRUNCATE stations, reservations RESTART IDENTITY CASCADE"))
        await session.commit()

    real_stations = await download_csv()

    all_stations: list[dict] = []
    if real_stations:
        all_stations.extend(real_stations)
        remaining = TARGET_STATIONS - len(real_stations)
        max_real_id = max(s["id"] for s in real_stations) + 1
        if remaining > 0:
            all_stations.extend(generate_synthetic(max_real_id, remaining))
    else:
        all_stations = generate_synthetic(1, TARGET_STATIONS)

    # Batch insert
    batch_size = 500
    async with session_factory() as session:
        for i in range(0, len(all_stations), batch_size):
            batch = all_stations[i : i + batch_size]
            values_parts = []
            for s in batch:
                total_slots = random.randint(10, 30)
                available = random.randint(0, total_slots)
                is_active = "true" if s["is_active"] else "false"
                name_escaped = s["name"].replace("'", "''")
                loc_escaped = (s.get("location") or "").replace("'", "''")
                values_parts.append(
                    f"({s['id']}, '{name_escaped}', '{loc_escaped}', "
                    f"ST_SetSRID(ST_MakePoint({s['longitude']}, {s['latitude']}), 4326), "
                    f"{total_slots}, {available}, {is_active})"
                )
            sql = (
                "INSERT INTO stations (id, name, location, geom, total_slots, available_bikes, is_active) "
                "VALUES " + ", ".join(values_parts) + " ON CONFLICT (id) DO NOTHING"
            )
            await session.execute(text(sql))
        await session.commit()

    # Reset sequence to max id
    async with session_factory() as session:
        await session.execute(
            text("SELECT setval('stations_id_seq', (SELECT COALESCE(MAX(id), 1) FROM stations))")
        )
        await session.execute(text("CLUSTER stations USING idx_stations_geom"))
        await session.execute(text("ANALYZE stations"))
        await session.commit()

    await engine.dispose()
    print(f"Seeded {len(all_stations)} stations ({len(real_stations or [])} real + {len(all_stations) - len(real_stations or [])} synthetic)")


if __name__ == "__main__":
    asyncio.run(seed())
