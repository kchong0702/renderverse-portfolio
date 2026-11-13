from src.features.write_networking.configurations import WriteNetworkingConfigurations
from src.features.write_networking.schemas import NetworkingCopy, WriteNetworkingInput
from src.shared.checks import CheckError, CheckRule


def check_coverage(
    copy: NetworkingCopy,
    request: WriteNetworkingInput,
    configurations: WriteNetworkingConfigurations,
) -> list[CheckError]:
    """Errors for each field asked for that the copy leaves out, and for each
    description of a fact that isn't a role or project"""
    written = copy.written()
    describable = request.describable()
    return [
        CheckError(
            rule=CheckRule.MISSING,
            at=field,
            message=f"write the {field}"
            if field in ("headline", "summary")
            else f"describe {field}",
        )
        for field in request.fields()
        if field not in written
    ] + [
        CheckError(
            rule=CheckRule.UNKNOWN_FACT,
            at=description.fact,
            message=f"{description.fact} is not a role or project to describe",
        )
        for description in copy.descriptions
        if description.fact not in describable
    ]
