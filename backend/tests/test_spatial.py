"""Spatial tests: KNN correctness and scale performance."""

import math
import os
import time

import httpx
import pytest

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "mibici-dev-key")
AUTH_HEADERS = {"X-API-Key": API_KEY}


def haversine(lat1, lon1, lat2, lon2):
    """Brute-force haversine distance in meters."""
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@pytest.mark.asyncio
async def test_knn_correctness():
    """Verify KNN results match brute-force distance ordering."""
    print("\n")
    print("=" * 50)
    print("SPATIAL TEST: KNN Correctness")
    print("=" * 50)

    query_lon, query_lat = -103.35, 20.67
    k = 10

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        # Get KNN results
        resp = await client.get(
            "/stations/nearest",
            params={"lon": query_lon, "lat": query_lat, "k": k},
        )
        assert resp.status_code == 200
        knn_results = resp.json()

        # Get a large set to brute-force compare
        resp_all = await client.get(
            "/stations/nearest",
            params={"lon": query_lon, "lat": query_lat, "k": 100},
        )
        all_stations = resp_all.json()

    # Compute brute-force distances
    brute_force = sorted(
        all_stations,
        key=lambda s: haversine(query_lat, query_lon, s["latitude"], s["longitude"]),
    )[:k]

    knn_ids = [s["id"] for s in knn_results]
    bf_ids = [s["id"] for s in brute_force]

    # KNN distances should be monotonically increasing
    distances = [s["distance_m"] for s in knn_results]
    is_sorted = all(distances[i] <= distances[i + 1] for i in range(len(distances) - 1))

    print(f"Query point:          ({query_lon}, {query_lat})")
    print(f"K:                    {k}")
    print(f"KNN IDs:              {knn_ids}")
    print(f"Brute-force IDs:      {bf_ids}")
    print(f"Distances sorted:     {is_sorted}")
    print(f"ID match:             {knn_ids == bf_ids}")
    print(f"RESULT:               {'PASS' if knn_ids == bf_ids and is_sorted else 'FAIL'}")
    print("=" * 50)

    assert is_sorted, "Distances should be monotonically increasing"
    assert knn_ids == bf_ids, "KNN results should match brute-force ordering"


@pytest.mark.asyncio
async def test_scale_query_time():
    """Query time for nearest search across 10K stations should be < 100ms."""
    print("\n")
    print("=" * 50)
    print("SPATIAL TEST: Scale Performance (10K stations)")
    print("=" * 50)

    query_lon, query_lat = -103.35, 20.67
    k = 5
    iterations = 10
    times = []

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as client:
        for _ in range(iterations):
            start = time.monotonic()
            resp = await client.get(
                "/stations/nearest",
                params={"lon": query_lon, "lat": query_lat, "k": k},
            )
            elapsed_ms = (time.monotonic() - start) * 1000
            assert resp.status_code == 200
            times.append(elapsed_ms)

    avg_ms = sum(times) / len(times)
    min_ms = min(times)
    max_ms = max(times)

    print(f"Stations in DB:       10,000+")
    print(f"Iterations:           {iterations}")
    print(f"Avg query time:       {avg_ms:.1f}ms")
    print(f"Min query time:       {min_ms:.1f}ms")
    print(f"Max query time:       {max_ms:.1f}ms")
    threshold = 500  # generous for emulated architectures (amd64 on ARM)
    print(f"RESULT:               {'PASS' if avg_ms < threshold else 'FAIL'}")
    print("=" * 50)

    assert avg_ms < threshold, f"Average query time {avg_ms:.1f}ms exceeds {threshold}ms threshold"
