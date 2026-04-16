import os

import httpx
import pytest

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "mibici-dev-key")
AUTH_HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def base_url():
    return BASE_URL


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30, headers=AUTH_HEADERS) as c:
        yield c
