from src.features.write_networking.configurations import WriteNetworkingConfigurations
from src.features.write_networking.schemas import NetworkingCopy, WriteNetworkingInput
from src.shared.checks import CheckError, CheckRule


def check_citations(
    copy: NetworkingCopy,
    request: WriteNetworkingInput,
    configurations: WriteNetworkingConfigurations,
) -> list[CheckError]:
    """Errors for each field asked for that cites a fact that doesn't exist"""
    ids = {fact.id for fact in request.facts}
    fields = request.fields()
    errors: list[CheckError] = []
    for field, passage in copy.written().items():
        if field not in fields:
            continue
        if unknown := [fact for fact in passage.facts if fact not in ids]:
            errors.append(
                CheckError(
                    rule=CheckRule.UNKNOWN_FACT,
                    at=field,
                    message=f"{', '.join(unknown)} are not facts in the profile",
                )
            )
    return errors
