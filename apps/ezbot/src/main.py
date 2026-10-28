import uvicorn

from src.core.config import get_settings

_settings = get_settings()


def main():
    """Start the uvicorn server"""
    uvicorn.run(
        "src.app.app:create_app",
        factory=True,
        host=_settings.app.host,
        port=_settings.app.port,
        workers=_settings.app.workers,
        log_level=_settings.app.log_level,
        access_log=_settings.app.access_log,
        loop="asyncio",
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
