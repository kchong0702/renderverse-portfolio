from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from fastapi import FastAPI

from src.app.a2a.executable import Executable, LanggraphExecutor
from src.core.config import AppSettings


def add_executable_routes(
    app: FastAPI, executables: list[Executable], settings: AppSettings
) -> None:
    """Serve each executable as its own A2A agent at <route_prefix>/a2a/<name>,
    with its agent card under that path"""
    for executable in executables:
        path = f"{settings.route_prefix}/a2a/{executable.name}"
        card = AgentCard(
            name=executable.name,
            description=executable.description,
            version=settings.version,
            supported_interfaces=[
                AgentInterface(
                    url=f"{settings.public_url}{path}",
                    protocol_binding="JSONRPC",
                    protocol_version="1.0",
                )
            ],
            capabilities=AgentCapabilities(streaming=True),
            default_input_modes=["application/json"],
            default_output_modes=["application/json"],
            skills=[
                AgentSkill(
                    id=executable.name,
                    name=executable.name,
                    description=executable.description,
                    tags=[executable.name],
                )
            ],
        )
        handler = DefaultRequestHandler(
            LanggraphExecutor(executable), InMemoryTaskStore(), card
        )
        add_a2a_routes_to_fastapi(
            app,
            agent_card_routes=create_agent_card_routes(
                card, card_url=f"{path}/.well-known/agent-card.json"
            ),
            jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url=path),
        )
