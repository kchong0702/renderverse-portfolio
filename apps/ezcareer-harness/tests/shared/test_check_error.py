import pytest
from pydantic import ValidationError

from src.shared.checks import CheckError, CheckRule


def test_a_check_error_names_a_known_rule():
    error = CheckError(rule="unknown_line", at="requirements[0]", message="-")

    assert error.rule is CheckRule.UNKNOWN_LINE


def test_a_check_error_refuses_an_unknown_rule():
    with pytest.raises(ValidationError):
        CheckError(rule="made_up", at="requirements[0]", message="-")
