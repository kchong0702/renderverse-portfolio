import httpx
from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import containers, providers
from document_schema import Changeset
from langgraph.checkpoint.memory import InMemorySaver

from src.agents import build_agent, load_agents
from src.agents.career_consultant import CareerConsultantState
from src.agents.career_consultant.tools import (
    ask_user,
    list_design_options_tool,
    read_pdf_lines,
)
from src.agents.job_finder import JobFinderState
from src.app.a2a import Executable
from src.clients.artifact_service import ArtifactServiceClient
from src.core.config import get_settings
from src.features import analyse_job, find_jobs, write_document
from src.shared.factory import Factory
from src.tools import read_profile_facts


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)
    """The app's settings"""

    registry = providers.Singleton(load_agents, settings.provided.agents)
    """Every registered agent, by name"""

    task_store = providers.Singleton(InMemoryTaskStore)
    """Where the A2A server keeps every task; swap in a database store here"""

    checkpointer = providers.Singleton(InMemorySaver)
    """Where graphs keep checkpoints so interrupted runs resume; pass it to
    each executable's graph, and swap in a database saver here"""

    job_sources = providers.Singleton(
        Factory[find_jobs.SearchProtocol], {"jsearch": find_jobs.JSearchAdapter}
    )
    """Job sources by name, each created once"""

    artifact_service_http_client = providers.Singleton(
        httpx.AsyncClient,
        base_url=settings.provided.artifact_service.url.encoded_string.call(),
        timeout=settings.provided.artifact_service.timeout_seconds,
    )
    """HTTP client on artifact-service's URL and render timeout"""

    artifact_service_client = providers.Singleton(
        ArtifactServiceClient, client=artifact_service_http_client
    )
    """Lists templates and prints documents through artifact-service"""

    job_finder = providers.Singleton(
        build_agent,
        agent=registry.provided["job-finder"],
        response_formats=(analyse_job.JobRequirements, find_jobs.RankedJobs),
        tools=(read_profile_facts,),
        state_schema=JobFinderState,
    )
    """The job-finder agent, built once"""

    career_consultant = providers.Singleton(
        build_agent,
        agent=registry.provided["career-consultant"],
        response_formats=(Changeset,),
        tools=providers.List(
            read_pdf_lines,
            read_profile_facts,
            providers.Callable(list_design_options_tool, artifact_service_client),
            ask_user,
        ),
        state_schema=CareerConsultantState,
    )
    """The career-consultant agent, built once"""

    executables = providers.List(
        providers.Singleton(
            Executable,
            kind="agent",
            name="job-finder",
            description="Talk to job-finder about how jobs fit the user's profile",
            graph=job_finder.provided.copy.call(
                update=providers.Dict(checkpointer=checkpointer)
            ),
        ),
        providers.Singleton(
            Executable,
            name="analyse-job",
            description="Show how well a job posting fits the user's profile, with every point cited",
            graph=providers.Singleton(
                analyse_job.build_graph, agent=job_finder, checkpointer=checkpointer
            ),
        ),
        providers.Singleton(
            Executable,
            name="find-jobs",
            description="Find fresh jobs for the user's profile and preferences, ranked by fit",
            graph=providers.Singleton(
                find_jobs.build_graph,
                agent=job_finder,
                job_sources=job_sources,
                checkpointer=checkpointer,
            ),
        ),
        providers.Singleton(
            Executable,
            kind="agent",
            name="career-consultant",
            description="Talk to career-consultant about the user's résumé or cover letter",
            graph=career_consultant.provided.copy.call(
                update=providers.Dict(checkpointer=checkpointer)
            ),
        ),
        providers.Singleton(
            Executable,
            name="edit-document",
            description="Propose a checked changeset for a chat request to change a résumé or cover letter",
            graph=providers.Singleton(
                write_document.build_graph,
                agent=career_consultant,
                artifact_service=artifact_service_client,
                checkpointer=checkpointer,
            ),
        ),
    )
    """Agents and workflows served over A2A; add a feature's Executable provider here"""
