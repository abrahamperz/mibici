from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import require_api_key
from app.db import async_session
from app.rate_limit import RateLimitMiddleware
from app.routes import stations, reservations
from app.schemas import HealthResponse

app = FastAPI(
    title="MIBICI API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(stations.router, dependencies=[Depends(require_api_key)])
app.include_router(reservations.router, dependencies=[Depends(require_api_key)])


@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        return HealthResponse(status="ok", db="connected")
    except Exception:
        return HealthResponse(status="degraded", db="disconnected")
