"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import common
from app.modules.sastadice.router import router as sastadice_router

api_router = APIRouter()

api_router.include_router(common.router, prefix="/common", tags=["common"])
api_router.include_router(sastadice_router, prefix="/sastadice", tags=["sastadice"])