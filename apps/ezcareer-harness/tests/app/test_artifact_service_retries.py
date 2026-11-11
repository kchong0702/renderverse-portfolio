import asyncio
import socket

from pydantic import HttpUrl

from src.app.container import Container
from src.core.config import ArtifactServiceSettings, get_settings


async def _no_templates(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    await reader.readuntil(b"\r\n\r\n")
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n[]")
    await writer.drain()
    writer.close()


async def _serve_after(delay: float, port: int) -> asyncio.Server:
    await asyncio.sleep(delay)
    return await asyncio.start_server(_no_templates, "127.0.0.1", port)


async def test_artifact_service_requests_retry_until_the_service_takes_connections():
    with socket.socket() as free:
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
    container = Container()
    container.settings.override(
        get_settings().model_copy(
            update={
                "artifact_service": ArtifactServiceSettings(
                    url=HttpUrl(f"http://127.0.0.1:{port}/artifact-service")
                )
            }
        )
    )
    starting = asyncio.create_task(_serve_after(0.2, port))

    templates = await container.clients.artifact_service().list_templates("resume")

    (await starting).close()
    assert templates == []
