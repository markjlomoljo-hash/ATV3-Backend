from fastapi import APIRouter

from app.api.v1.routes import (
    assistant,
    auth,
    evidence,
    forecast,
    intelligence,
    logs,
    network,
    onboarding,
    products,
    profile,
    reports,
    scans,
)

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(onboarding.router)
api_router.include_router(logs.router)
api_router.include_router(scans.router)
api_router.include_router(products.router)
api_router.include_router(forecast.router)
api_router.include_router(assistant.router)
api_router.include_router(evidence.router)
api_router.include_router(intelligence.router)
api_router.include_router(network.router)
api_router.include_router(reports.router)
