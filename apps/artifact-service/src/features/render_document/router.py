from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.features.render_document.exceptions import RenderError
from src.features.render_document.schemas import RenderRequest, RenderResponse
from src.features.render_document.service import render_document
from src.shared.browser import Browser


def get_browser(request: Request) -> Browser:
    return request.app.state.browser


router = APIRouter(tags=["render"])


@router.post("/render")
async def render(
    request: RenderRequest,
    browser: Annotated[Browser, Depends(get_browser)],
) -> RenderResponse:
    """Render a document to HTML and PDF and measure the result"""
    try:
        return await render_document(request, browser)
    except RenderError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
