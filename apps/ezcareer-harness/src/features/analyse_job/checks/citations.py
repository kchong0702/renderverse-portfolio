from src.features.analyse_job.enums import Match
from src.features.analyse_job.schemas import JobRequirements, PostingLine
from src.shared.checks import CheckError, CheckRule
from src.shared.models import ProfileFact


def check_citations(
    output: JobRequirements, lines: list[PostingLine], facts: list[ProfileFact]
) -> list[CheckError]:
    """Errors for cited lines or facts that don't exist, and for requirement
    text that isn't word for word in the lines it cites"""
    texts = {line.id: line.text for line in lines}
    fact_ids = {f"fact:{fact.id}" for fact in facts}
    errors: list[CheckError] = []
    for index, requirement in enumerate(output.requirements):
        at = f"requirements[{index}]"
        unknown_lines = [i for i in requirement.line_ids if i not in texts]
        if unknown_lines:
            errors.append(
                CheckError(
                    rule=CheckRule.UNKNOWN_LINE,
                    at=at,
                    message=f"lines {unknown_lines} are not in the posting",
                )
            )
        else:
            cited = " ".join(" ".join(texts[i].split()) for i in requirement.line_ids)
            if " ".join(requirement.text.split()) not in cited:
                errors.append(
                    CheckError(
                        rule=CheckRule.NOT_VERBATIM,
                        at=at,
                        message=f"{requirement.text!r} is not word for word in lines {requirement.line_ids}",
                    )
                )
        unknown_facts = [f for f in requirement.fact_ids if f not in fact_ids]
        if unknown_facts:
            errors.append(
                CheckError(
                    rule=CheckRule.UNKNOWN_FACT,
                    at=at,
                    message=f"{unknown_facts} are not facts in the profile",
                )
            )
        if requirement.match is not Match.NOT_MET and not requirement.fact_ids:
            errors.append(
                CheckError(
                    rule=CheckRule.UNCITED_MATCH,
                    at=at,
                    message=f"{requirement.match} needs the facts that show it",
                )
            )
    for name, term in output.terms:
        unknown_lines = [i for i in term.line_ids if i not in texts] if term else []
        if unknown_lines:
            errors.append(
                CheckError(
                    rule="unknown_line",
                    at=f"terms.{name}",
                    message=f"lines {unknown_lines} are not in the posting",
                )
            )
    return errors
