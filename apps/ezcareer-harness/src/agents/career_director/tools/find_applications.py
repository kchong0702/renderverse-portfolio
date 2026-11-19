from zoneinfo import ZoneInfo

from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import ValidationError
from pydantic_core import to_json

from src.agents.career_director.types import (
    ApplicationStage,
    ApplicationStep,
    FoundApplications,
)
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail


def _in_zone(step: ApplicationStep, zone: ZoneInfo) -> ApplicationStep:
    """The step with its start in the zone"""
    return step.model_copy(
        update={"starts_at": step.starts_at and step.starts_at.astimezone(zone)}
    )


@tool(response_format="content_and_artifact")
def find_applications(
    company: str | None = None, stage: ApplicationStage | None = None
) -> tuple[str, StepDetail]:
    """Finds the applications the user tracks, by part of a company's name, a stage or
    both, with how many there are at each stage and each one's next step"""
    try:
        found = FoundApplications.model_validate(
            interrupt(
                {"execute_tool": "applications", "company": company, "stage": stage}
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The applications didn't load: {error}") from error
    applications = [
        application.model_copy(
            update={
                "next_step": application.next_step
                and _in_zone(application.next_step, found.timezone),
                "overdue": [
                    _in_zone(step, found.timezone) for step in application.overdue
                ],
            }
        )
        for application in found.applications
    ]
    count = len(applications)
    return f"Times are in {found.timezone.key}.\n" + to_json(
        {
            "total": sum(found.by_stage.values()),
            "by_stage": found.by_stage,
            "applications": applications,
        }
    ).decode(), {
        "step_detail": f"{count} applications" if count != 1 else "1 application"
    }
