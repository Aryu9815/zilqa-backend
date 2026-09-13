from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.database import fetch_val

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic service health check")
async def health_check():
    """Liveness probe to check if the application server is up."""
    return {"status": "ok"}


@router.get("/health/db", summary="Database connection health check")
async def db_health_check():
    """Readiness probe to verify PostgreSQL database connectivity via asyncpg."""
    try:
        val = await fetch_val("SELECT 1")
        if val == 1:
            return {"status": "ok", "database": "connected"}
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "database": "unexpected response"}
            )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "error", "database": "unavailable", "detail": str(exc)}
        )
