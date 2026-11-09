from fastapi import APIRouter

from src.features.list_templates import router as templates_router
from src.features.render_document import router as render_router

router = APIRouter(prefix="/v1")
router.include_router(render_router)
router.include_router(templates_router)
