from fastapi import APIRouter

from src.app.api.routes.chat import router as chat_router
from src.app.api.routes.session import router as session_router

api_router = APIRouter()

api_router.include_router(session_router, prefix="/v1", tags=["session"])
api_router.include_router(chat_router, prefix="/v1", tags=["chat"])
