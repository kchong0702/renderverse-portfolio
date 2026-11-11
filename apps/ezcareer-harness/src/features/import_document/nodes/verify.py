from document_schema import Design, DocumentKind, ResumeContent, ResumeDocument
from pydantic import ValidationError

from src.features.import_document.checks import (
    check_coverage,
    check_order,
    check_verbatim,
)
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.state import ImportState
from src.shared.checks import CheckError, CheckRule, check_round

CHECKS = {
    "verbatim": check_verbatim,
    "coverage": check_coverage,
    "order": check_order,
}
"""Every check the import-resume configurations.yaml may turn on, by name"""


def verify(
    state: ImportState, configurations: ImportResumeConfigurations
) -> ImportState:
    """Checks the last reply against the file's lines and makes the draft, in the
    suggested template, once it passes; errors go back to the LLM"""
    if (reply := state["structured_response"]) is None:
        return check_round(
            [CheckError(rule=CheckRule.SCHEMA, at="", message=state["parsing_error"])]
        )
    if errors := [
        error
        for name in configurations.checks
        for error in CHECKS[name](reply, state["lines"], configurations)
    ]:
        return check_round(errors)
    try:
        document = ResumeDocument(
            kind=DocumentKind.RESUME,
            content=ResumeContent(blocks=reply.blocks),
            design=Design(template=state["suggestion"].template),
        )
    except ValidationError as error:
        return check_round(
            [
                CheckError(
                    rule=CheckRule.SCHEMA,
                    at="/".join(str(part) for part in issue["loc"]),
                    message=issue["msg"],
                )
                for issue in error.errors()
            ]
        )
    return {**check_round([]), "document": document}
