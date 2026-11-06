from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from src.core.config import get_settings
from src.features.render_document.browser import Browser
from src.features.render_document.schemas import RenderRequest, RenderResponse
from src.features.render_document.service import render_document


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[dict[str, Browser]]:
    """Keeps one Chromium for the app's lifetime"""
    browser = Browser(get_settings().renderer.max_concurrent_renders)
    yield {"browser": browser}
    await browser.close()


def _browser(request: Request) -> Browser:
    """The app's Chromium"""
    return request.state.browser


router = APIRouter(tags=["render"], lifespan=_lifespan)


@router.post("/render")
async def render(
    request: RenderRequest, browser: Annotated[Browser, Depends(_browser)]
) -> RenderResponse:
    """Print a document with a template as a PDF and report how its pages came out"""
    try:
        return await render_document(request, browser)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="the render took too long") from exc
