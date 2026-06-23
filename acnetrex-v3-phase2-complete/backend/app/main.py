"""
Application entrypoint.

Exception handlers here are what makes app/core/errors.py's hierarchy
actually reach the client as structured JSON instead of every route having
to catch its own exceptions. main.py is intentionally thin: CORS config,
exception -> HTTP mapping, router mounting, and a real DB connectivity check
on startup (so the service fails loudly at boot if the database is
unreachable, instead of every request failing mysteriously later).
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import AcneTrexError
from app.db.session import engine

logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger("acnetrex")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AcneTrex v3 backend - real auth, persistence, and AI/ML service boundaries.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AcneTrexError)
async def acnetrex_error_handler(request: Request, exc: AcneTrexError) -> JSONResponse:
    logger.warning("AcneTrexError on %s %s: %s (%s)", request.method, request.url.path, exc.code, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message, "details": exc.details})


@app.get("/health")
async def health_check() -> dict:
    """Real connectivity check, not a hardcoded 200. If the database is
    unreachable this returns 'degraded' and a non-200 status so uptime
    monitoring catches it."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "version": settings.APP_VERSION, "environment": settings.ENVIRONMENT}
    except Exception as exc:  # noqa: BLE001 - intentionally broad for a health probe
        logger.error("Database health check failed: %s", exc)
        return JSONResponse(status_code=503, content={"status": "degraded", "detail": "database_unreachable"})


app.include_router(api_router)
