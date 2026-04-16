"""Integration tests: full flow, edge cases, health check."""

import os

import httpx
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "mibici-dev-key")
AUTH_HEADERS = {"X-API-Key": API_KEY}


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10, headers=AUTH_HEADERS) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"


@pytest.mark.asyncio
async def test_full_flow():
    """Create -> search nearby -> reserve -> return -> verify availability."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        # Create a station
        create_resp = await client.post(
            "/stations",
            json={
                "name": "Integration Test Station",
                "location": "Centro, Guadalajara",
                "longitude": -103.3494,
                "latitude": 20.6737,
                "total_slots": 15,
                "available_bikes": 10,
            },
        )
        assert create_resp.status_code == 201
        station = create_resp.json()
        station_id = station["id"]
        assert station["available_bikes"] == 10

        # Search nearby — should find our station
        search_resp = await client.get(
            "/stations/nearest",
            params={"lon": -103.3494, "lat": 20.6737, "k": 5},
        )
        assert search_resp.status_code == 200
        results = search_resp.json()
        found_ids = [s["id"] for s in results]
        assert station_id in found_ids

        # Reserve a bike
        reserve_resp = await client.post(f"/stations/{station_id}/reserve")
        assert reserve_resp.status_code == 201
        reservation = reserve_resp.json()
        assert reservation["status"] == "active"

        # Check availability decreased
        get_resp = await client.get(f"/stations/{station_id}")
        assert get_resp.json()["available_bikes"] == 9

        # Return the bike
        return_resp = await client.post(f"/stations/{station_id}/return")
        assert return_resp.status_code == 200

        # Check availability restored
        get_resp = await client.get(f"/stations/{station_id}")
        assert get_resp.json()["available_bikes"] == 10

        # Clean up
        del_resp = await client.delete(f"/stations/{station_id}")
        assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_reserve_empty_station():
    """Reserving from a station with 0 bikes should return 409."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        create_resp = await client.post(
            "/stations",
            json={
                "name": "Empty Station",
                "longitude": -103.35,
                "latitude": 20.67,
                "total_slots": 10,
                "available_bikes": 0,
            },
        )
        station_id = create_resp.json()["id"]

        resp = await client.post(f"/stations/{station_id}/reserve")
        assert resp.status_code == 409

        await client.delete(f"/stations/{station_id}")


@pytest.mark.asyncio
async def test_return_full_station():
    """Returning to a full station should return 409."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        create_resp = await client.post(
            "/stations",
            json={
                "name": "Full Station",
                "longitude": -103.35,
                "latitude": 20.67,
                "total_slots": 10,
                "available_bikes": 10,
            },
        )
        station_id = create_resp.json()["id"]

        resp = await client.post(f"/stations/{station_id}/return")
        assert resp.status_code == 409

        await client.delete(f"/stations/{station_id}")


@pytest.mark.asyncio
async def test_nonexistent_station():
    """Operations on a nonexistent station should return 404."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        resp = await client.get("/stations/999999")
        assert resp.status_code == 404

        resp = await client.post("/stations/999999/reserve")
        assert resp.status_code == 404

        resp = await client.delete("/stations/999999")
        assert resp.status_code == 404
