from fastapi import APIRouter

from src.core.auth import router as auth_router
from src.features.settings import router as settings_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
