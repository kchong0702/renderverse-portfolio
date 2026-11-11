from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from src.features.render_document.browser import Browser
from src.features.render_document.schemas import RenderRequest, RenderResponse
from src.features.render_document.service import render_document


def _browser(request: Request) -> Browser:
    """The app's Chromium"""
    return request.app.state.browser


router = APIRouter(tags=["render"])


@router.post("/render")
async def render(
    request: RenderRequest, browser: Annotated[Browser, Depends(_browser)]
) -> RenderResponse:
    """Print a document in its design's template as a PDF and report how its pages came out"""
    try:
        return await render_document(request, browser)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="the render took too long") from exc
