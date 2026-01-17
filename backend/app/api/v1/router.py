"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import common

api_router = APIRouter()

api_router.include_router(common.router, prefix="/common", tags=["common"])
