import os

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "mibici-dev-key")

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str | None = Security(_header)):
    if not key or key != API_KEY:
        raise HTTPException(401, "Invalid or missing API key")
