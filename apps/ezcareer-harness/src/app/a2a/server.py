from a2a.server.cluster import TaskEventStream, VersionedTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    add_a2a_routes_to_fastapi,
    create_agent_card_routes,
    create_jsonrpc_routes,
)
from a2a.server.tasks import TaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from fastapi import FastAPI

from src.app.a2a.executable import Executable
from src.app.a2a.executor import LanggraphExecutor
from src.app.a2a.task_supervisor import TaskSupervisor
from src.core.config import AppSettings
from src.infrastructure.stores import ThreadLock


def add_executable_routes(
    app: FastAPI,
    executables: list[Executable],
    task_store: TaskStore | VersionedTaskStore,
    event_stream: TaskEventStream | None,
    supervisor: TaskSupervisor,
    thread_lock: ThreadLock,
    settings: AppSettings,
) -> dict[str, DefaultRequestHandler]:
    """Serves each executable as an A2A agent at <route_prefix>/a2a/<name>, its
    tasks shared across replicas; returns each handler by name"""
    handlers: dict[str, DefaultRequestHandler] = {}
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
        handlers[executable.name] = DefaultRequestHandler(
            LanggraphExecutor(executable, supervisor, thread_lock),
            task_store,
            card,
            event_stream=event_stream,
        )
        add_a2a_routes_to_fastapi(
            app,
            agent_card_routes=create_agent_card_routes(
                card, card_url=f"{path}/.well-known/agent-card.json"
            ),
            jsonrpc_routes=create_jsonrpc_routes(
                handlers[executable.name], rpc_url=path
            ),
        )
    return handlers
