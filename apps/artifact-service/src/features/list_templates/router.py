from document_schema import DocumentKind, TemplateSpec
from fastapi import APIRouter

from src.shared.templates import templates

router = APIRouter(tags=["templates"])


@router.get("/templates")
async def list_templates(kind: DocumentKind | None = None) -> list[TemplateSpec]:
    """The templates a document can be printed with, only those for kind when given"""
    return [spec for spec in templates().values() if kind is None or kind in spec.kinds]
