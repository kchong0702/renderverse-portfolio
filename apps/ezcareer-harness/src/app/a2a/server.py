from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from fastapi import FastAPI

from src.app.a2a.flow import Flow, FlowExecutor
from src.core.config import AppSettings


def add_flow_routes(app: FastAPI, flows: list[Flow], settings: AppSettings) -> None:
    """Serve each flow as its own A2A agent at <route_prefix>/a2a/<name>,
    with its agent card under that path"""
    for flow in flows:
        path = f"{settings.route_prefix}/a2a/{flow.name}"
        card = AgentCard(
            name=flow.name,
            description=flow.description,
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
                    id=flow.name,
                    name=flow.name,
                    description=flow.description,
                    tags=[flow.name],
                )
            ],
        )
        handler = DefaultRequestHandler(FlowExecutor(flow), InMemoryTaskStore(), card)
        add_a2a_routes_to_fastapi(
            app,
            agent_card_routes=create_agent_card_routes(
                card, card_url=f"{path}/.well-known/agent-card.json"
            ),
            jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url=path),
        )
