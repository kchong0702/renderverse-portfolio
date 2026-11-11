from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.email_assistant.tools import (
    read_free_slots_tool,
    read_thread_tool,
    search_threads_tool,
)
from src.agents.state import ProfileState
from src.app.a2a import Executable
from src.core.config import Settings
from src.features import draft_reply, triage_email
from src.tools import read_profile_facts


class EmailAssistantContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)
    """The app's settings"""

    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graphs keep checkpoints"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["email-assistant"],
        response_formats=(draft_reply.DraftReply, triage_email.EmailReading),
        tools=providers.List(
            read_profile_facts,
            providers.Callable(
                search_threads_tool, settings.provided.email.max_threads
            ),
            providers.Callable(
                read_thread_tool,
                settings.provided.email.max_thread_messages,
                settings.provided.email.max_message_chars,
            ),
            providers.Callable(
                read_free_slots_tool, settings.provided.email.max_free_slots
            ),
        ),
        state_schema=ProfileState,
    )
    """The email-assistant agent, built once"""

    triage_email_executable = providers.Singleton(
        Executable,
        name="triage-email",
        description="Say whether an email thread needs a reply, confirms an interview or makes an offer, and which application it is about",
        graph=providers.Singleton(
            triage_email.build_graph, agent=agent, checkpointer=checkpointer
        ),
    )
    """The triage-email workflow served over A2A"""

    draft_reply_executable = providers.Singleton(
        Executable,
        name="draft-reply",
        description="Draft the user's reply to an email thread, or a follow-up for an application with no reply, offering free times when asked; it sends nothing",
        graph=providers.Singleton(
            draft_reply.build_graph, agent=agent, checkpointer=checkpointer
        ),
    )
    """The draft-reply workflow served over A2A"""
