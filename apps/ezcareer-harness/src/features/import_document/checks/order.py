from itertools import pairwise

from src.features.import_document.checks.values import cited_values
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.schemas import ImportedResume
from src.shared.checks import CheckError, CheckRule
from src.shared.extraction import Line


def check_order(
    reply: ImportedResume,
    lines: list[Line],
    configurations: ImportResumeConfigurations,
) -> list[CheckError]:
    """Each block starts after the block before it"""
    order = {line.id: index for index, line in enumerate(lines)}
    starts = [
        (block.id, min(found))
        for block in reply.blocks
        if (
            found := [
                order[source]
                for _, value in cited_values(block, "")
                for source in value.src
                if source in order
            ]
        )
    ]
    return [
        CheckError(
            rule=CheckRule.ORDER,
            at=f"blocks/{block}",
            message=f"starts at {lines[start].id}, before {previous} at"
            f" {lines[previous_start].id}, so it must come first",
        )
        for (previous, previous_start), (block, start) in pairwise(starts)
        if start < previous_start
    ]
