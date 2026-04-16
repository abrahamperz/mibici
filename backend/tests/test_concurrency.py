"""Concurrency tests: race conditions, oversell prevention, throughput."""

import asyncio
import os
import time

import httpx
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "mibici-dev-key")
AUTH_HEADERS = {"X-API-Key": API_KEY}


async def _create_station(bikes: int, slots: int = 20) -> int:
    """Create a test station and return its ID."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        resp = await client.post(
            "/stations",
            json={
                "name": f"Test Station {time.monotonic_ns()}",
                "longitude": -103.35,
                "latitude": 20.67,
                "total_slots": slots,
                "available_bikes": bikes,
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]


async def _reserve(station_id: int) -> int:
    """Make a reservation request with its own client. Returns status code."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        resp = await client.post(f"/stations/{station_id}/reserve")
        return resp.status_code


async def _get_station(station_id: int) -> dict:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        resp = await client.get(f"/stations/{station_id}")
        return resp.json()


async def _search_nearest() -> tuple[int, list]:
    """Search nearest stations. Returns (status_code, stations)."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        resp = await client.get(
            "/stations/nearest", params={"lon": -103.35, "lat": 20.67, "k": 10}
        )
        return resp.status_code, resp.json() if resp.status_code == 200 else []


@pytest.mark.asyncio
async def test_last_bike_race():
    """50 concurrent requests for 1 bike. Exactly 1 must succeed."""
    station_id = await _create_station(bikes=1)
    concurrent = 50

    print("\n")
    print("=" * 50)
    print("CONCURRENCY TEST: Last-Bike Race")
    print("=" * 50)

    start = time.monotonic()
    results = await asyncio.gather(*[_reserve(station_id) for _ in range(concurrent)])
    elapsed_ms = (time.monotonic() - start) * 1000

    success = results.count(201)
    conflict = results.count(409)

    station = await _get_station(station_id)
    final_bikes = station["available_bikes"]

    print(f"Concurrent requests:   {concurrent}")
    print(f"Successful reserves:   {success}")
    print(f"Conflict (409):        {conflict}")
    print(f"Final available_bikes: {final_bikes}")
    print(f"Wall time:             {elapsed_ms:.0f}ms")
    print(f"RESULT:                {'PASS' if success == 1 and final_bikes == 0 else 'FAIL'}")
    print("=" * 50)

    assert success == 1, f"Expected exactly 1 success, got {success}"
    assert conflict == concurrent - 1
    assert final_bikes == 0


@pytest.mark.asyncio
async def test_no_oversell():
    """200 concurrent requests for 10 bikes. Exactly 10 must succeed."""
    bikes = 10
    concurrent = 200
    station_id = await _create_station(bikes=bikes)

    print("\n")
    print("=" * 50)
    print("CONCURRENCY TEST: No-Oversell Proof")
    print("=" * 50)

    start = time.monotonic()
    results = await asyncio.gather(*[_reserve(station_id) for _ in range(concurrent)])
    elapsed_ms = (time.monotonic() - start) * 1000

    success = results.count(201)
    conflict = results.count(409)

    station = await _get_station(station_id)
    final_bikes = station["available_bikes"]

    print(f"Concurrent requests:   {concurrent}")
    print(f"Available bikes:       {bikes}")
    print(f"Successful reserves:   {success}")
    print(f"Conflict (409):        {conflict}")
    print(f"Final available_bikes: {final_bikes}")
    print(f"Wall time:             {elapsed_ms:.0f}ms")
    print(f"RESULT:                {'PASS' if success == bikes and final_bikes == 0 else 'FAIL'}")
    print("=" * 50)

    assert success == bikes, f"Expected {bikes} successes, got {success}"
    assert conflict == concurrent - bikes
    assert final_bikes == 0


@pytest.mark.asyncio
async def test_search_under_mutation():
    """Concurrent reads (nearest search) while writes (reservations) happen."""
    station_id = await _create_station(bikes=15, slots=20)

    print("\n")
    print("=" * 50)
    print("CONCURRENCY TEST: Search Under Mutation")
    print("=" * 50)

    # Mix reads and writes
    reserve_tasks = [_reserve(station_id) for _ in range(15)]
    search_tasks = [_search_nearest() for _ in range(20)]

    start = time.monotonic()
    all_results = await asyncio.gather(*reserve_tasks, *search_tasks)
    elapsed_ms = (time.monotonic() - start) * 1000

    reserve_results = all_results[:15]
    search_results = all_results[15:]

    errors_500 = sum(1 for r in reserve_results if r >= 500)
    search_errors = sum(1 for code, _ in search_results if code >= 500)
    negative_bikes = 0
    for _, stations in search_results:
        for s in stations:
            if s.get("available_bikes", 0) < 0:
                negative_bikes += 1

    print(f"Reserve requests:      15")
    print(f"Search requests:       20")
    print(f"Server errors (5xx):   {errors_500 + search_errors}")
    print(f"Negative bike counts:  {negative_bikes}")
    print(f"Wall time:             {elapsed_ms:.0f}ms")
    print(f"RESULT:                {'PASS' if errors_500 + search_errors + negative_bikes == 0 else 'FAIL'}")
    print("=" * 50)

    assert errors_500 == 0, "Reserve requests should not cause 500 errors"
    assert search_errors == 0, "Search requests should not cause 500 errors"
    assert negative_bikes == 0, "available_bikes should never be negative"


@pytest.mark.asyncio
async def test_throughput():
    """1000 reserves across 100 different stations. Measure wall time."""
    print("\n")
    print("=" * 50)
    print("CONCURRENCY TEST: Throughput Benchmark")
    print("=" * 50)

    num_stations = 100
    reserves_per_station = 10

    station_ids = await asyncio.gather(
        *[_create_station(bikes=reserves_per_station) for _ in range(num_stations)]
    )

    tasks = []
    for sid in station_ids:
        for _ in range(reserves_per_station):
            tasks.append(_reserve(sid))

    start = time.monotonic()
    results = await asyncio.gather(*tasks)
    elapsed = time.monotonic() - start

    success = sum(1 for r in results if r == 201)
    total = len(tasks)
    rps = total / elapsed if elapsed > 0 else 0

    print(f"Total requests:        {total}")
    print(f"Stations:              {num_stations}")
    print(f"Successful reserves:   {success}")
    print(f"Wall time:             {elapsed:.2f}s")
    print(f"Throughput:            {rps:.0f} req/s")
    print(f"RESULT:                {'PASS' if success == total else 'FAIL'}")
    print("=" * 50)

    assert success == total
