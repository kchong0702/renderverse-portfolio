from fastapi import APIRouter

from src.core.auth import router as auth_router
from src.features.applications.router import router as applications_router
from src.features.assistant import router as assistant_router
from src.features.calendar import router as calendar_router
from src.features.documents import router as documents_router
from src.features.google import router as google_router
from src.features.imports import router as imports_router
from src.features.inbox import router as inbox_router
from src.features.jobs import router as jobs_router
from src.features.portfolio import router as portfolio_router
from src.features.preferences import router as preferences_router
from src.features.profile import router as profile_router
from src.features.settings import router as settings_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(applications_router)
api_router.include_router(assistant_router)
api_router.include_router(documents_router)
api_router.include_router(imports_router)
api_router.include_router(jobs_router)
api_router.include_router(portfolio_router)
api_router.include_router(preferences_router)
api_router.include_router(profile_router)
api_router.include_router(calendar_router)
api_router.include_router(google_router)
api_router.include_router(inbox_router)
api_router.include_router(settings_router)

__all__ = ["api_router"]
