from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.state import ProfileState
from src.app.a2a import Executable
from src.features import triage_email
from src.tools import read_profile_facts


class EmailAssistantContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graphs keep checkpoints"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["email-assistant"],
        response_formats=(triage_email.EmailReading,),
        tools=(read_profile_facts,),
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
