from src.features.import_document.checks import (
    check_coverage,
    check_order,
    check_verbatim,
)
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.state import ImportState
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round

CHECKS = {
    "verbatim": check_verbatim,
    "coverage": check_coverage,
    "order": check_order,
}
"""Every check the import-resume configurations.yaml may turn on, by name"""


def verify(
    state: ImportState, configurations: ImportResumeConfigurations
) -> CheckRound:
    """Checks the last reply against the file's lines; errors go back to the LLM"""
    if (reply := state["structured_response"]) is None:
        return check_round(
            [CheckError(rule=CheckRule.SCHEMA, at="", message=state["parsing_error"])]
        )
    return check_round(
        [
            error
            for name in configurations.checks
            for error in CHECKS[name](reply, state["lines"], configurations)
        ]
    )
