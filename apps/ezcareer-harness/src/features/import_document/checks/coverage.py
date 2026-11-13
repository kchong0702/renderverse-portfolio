from src.features.import_document.checks.values import cited_values
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.schemas import ImportedResume
from src.shared.checks import CheckError, CheckRule
from src.shared.extraction import Line


def check_coverage(
    reply: ImportedResume,
    lines: list[Line],
    configurations: ImportResumeConfigurations,
) -> list[CheckError]:
    """Each line is cited by some value or skipped, and each skipped id is a line"""
    ids = {line.id for line in lines}
    cited = {
        source
        for _, value in cited_values(reply.blocks, "blocks")
        for source in value.src
    }
    errors: list[CheckError] = []
    if unknown := [source for source in reply.skipped if source not in ids]:
        errors.append(
            CheckError(
                rule=CheckRule.COVERAGE,
                at="skipped",
                message=f"{', '.join(unknown)} are not lines",
            )
        )
    if dropped := [
        f"{line.id} {line.text!r}"
        for line in lines
        if line.id not in cited and line.id not in reply.skipped
    ]:
        errors.append(
            CheckError(
                rule=CheckRule.COVERAGE,
                at="blocks",
                message="cite or skip each of these lines: " + "; ".join(dropped),
            )
        )
    return errors
