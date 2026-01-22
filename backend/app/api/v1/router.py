"""API v1 router."""

from fastapi import APIRouter

from app.modules.common.api.router import router as common_router
from app.modules.sastadice.router import router as sastadice_router

api_router = APIRouter()

api_router.include_router(common_router, prefix="/common", tags=["common"])
api_router.include_router(sastadice_router, prefix="/sastadice", tags=["sastadice"])
