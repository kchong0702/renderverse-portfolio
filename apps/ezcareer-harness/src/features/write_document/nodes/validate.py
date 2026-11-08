from typing import Literal

from src.features.write_document.checks import sources
from src.features.write_document.configurations import CHECKS
from src.features.write_document.state import EditGraphState
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round


def validate(state: EditGraphState, checks: list[Literal["changeset"]]) -> CheckRound:
    """Runs the checks on the agent's changeset; errors go back to the agent"""
    changeset = state.get("structured_response")
    if changeset is None:
        return check_round(
            [
                CheckError(
                    rule=CheckRule.NO_CHANGESET,
                    at="answer",
                    message="Reply with a Changeset",
                )
            ]
        )
    return check_round(
        [
            error
            for name in checks
            for error in CHECKS[name](state["document"], changeset, sources(state))
        ]
    )
