from src.features.import_document.checks.text import letters_and_digits
from src.features.import_document.checks.values import cited_values
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.schemas import ResumeImport
from src.shared.checks import CheckError, CheckRule
from src.shared.extraction import Line


def check_verbatim(
    reply: ResumeImport,
    lines: list[Line],
    configurations: ImportResumeConfigurations,
) -> list[CheckError]:
    """Each value has text, and its text appears in the lines it cites"""
    order = {line.id: index for index, line in enumerate(lines)}
    errors: list[CheckError] = []
    for path, value in cited_values(reply.blocks, "blocks"):
        if unknown := [source for source in value.src if source not in order]:
            message = f"cites {', '.join(unknown)}, which are not lines"
        elif not value.src:
            message = "cites no lines"
        elif not letters_and_digits(value.text):
            message = "has no text"
        elif letters_and_digits(value.text) not in letters_and_digits(
            "".join(lines[index].text for index in sorted(order[s] for s in value.src))
        ):
            message = f"{value.text!r} is not the text of {', '.join(value.src)}"
        else:
            continue
        errors.append(CheckError(rule=CheckRule.VERBATIM, at=path, message=message))
    return errors
