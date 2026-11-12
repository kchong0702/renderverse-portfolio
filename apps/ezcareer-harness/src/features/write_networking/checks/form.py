import re

from src.features.write_networking.configurations import WriteNetworkingConfigurations
from src.features.write_networking.schemas import NetworkingCopy, WriteNetworkingInput
from src.shared.checks import CheckError, CheckRule

MARKUP = re.compile(
    r"^\s*(?:[-*+>#]|\d+[.)])\s|\*\*|__|`|\[[^\]]*\]\(|</?[A-Za-z]", re.MULTILINE
)
"""Markdown list markers, headings, emphasis, code and links, and HTML tags"""


def check_form(
    copy: NetworkingCopy,
    request: WriteNetworkingInput,
    configurations: WriteNetworkingConfigurations,
) -> list[CheckError]:
    """Errors for each field asked for that runs over its cap or isn't plain text"""
    caps = {
        "headline": configurations.max_headline_chars,
        "summary": configurations.max_summary_chars,
    }
    fields = request.fields()
    errors: list[CheckError] = []
    for field, passage in copy.written().items():
        if field not in fields:
            continue
        cap = caps.get(field, configurations.max_description_chars)
        if len(passage.text) > cap:
            errors.append(
                CheckError(
                    rule=CheckRule.TOO_LONG,
                    at=field,
                    message=f"is {len(passage.text)} characters; cut it to {cap} at"
                    " most",
                )
            )
        if found := MARKUP.search(passage.text):
            errors.append(
                CheckError(
                    rule=CheckRule.NOT_PLAIN,
                    at=field,
                    message=f"{found.group().strip()!r} is Markdown or HTML; write"
                    " plain text, with bullets as •",
                )
            )
    return errors
