from fastapi import APIRouter, HTTPException

from src.features.convert_document.exceptions import UnconvertibleFile
from src.features.convert_document.schemas import ConvertRequest, ConvertResponse
from src.features.convert_document.service import convert_document

router = APIRouter(tags=["convert"])


@router.post("/convert")
def convert(request: ConvertRequest) -> ConvertResponse:
    """Convert a Word file to PDF, and return a PDF as it is"""
    try:
        return ConvertResponse(pdf=convert_document(request.file))
    except UnconvertibleFile as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
