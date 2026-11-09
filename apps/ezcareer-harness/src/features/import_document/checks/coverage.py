from src.features.import_document.checks.text import letters_and_digits
from src.features.import_document.checks.values import cited_values
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.schemas import ResumeImport
from src.shared.checks import CheckError, CheckRule
from src.shared.extraction import Line


def check_coverage(
    reply: ResumeImport,
    lines: list[Line],
    configurations: ImportResumeConfigurations,
) -> list[CheckError]:
    """Each line is cited with all its words but short joining ones, or skipped
    for being short or repeated"""
    order = {line.id: index for index, line in enumerate(lines)}
    texts = [
        "".join(letters_and_digits(word) for word in line.text.split())
        for line in lines
    ]
    used = [[False] * len(text) for text in texts]
    for _, value in cited_values(reply.blocks, "blocks"):
        indexes = sorted({order[source] for source in value.src if source in order})
        text = letters_and_digits(value.text)
        start = "".join(texts[index] for index in indexes).find(text)
        if start < 0 or not text:
            continue
        end, offset = start + len(text), 0
        for index in indexes:
            for position in range(
                max(start, offset), min(end, offset + len(texts[index]))
            ):
                used[index][position - offset] = True
            offset += len(texts[index])
    cited = {
        source
        for _, value in cited_values(reply.blocks, "blocks")
        for source in value.src
    }
    errors: list[CheckError] = []
    if unknown := [source for source in reply.skipped if source not in order]:
        errors.append(
            CheckError(
                rule=CheckRule.COVERAGE,
                at="skipped",
                message=f"{', '.join(unknown)} are not lines",
            )
        )
    if content := [
        lines[order[source]]
        for source in reply.skipped
        if source in order
        and len(texts[order[source]]) > configurations.max_skipped_length
        and texts.count(texts[order[source]]) == 1
    ]:
        errors.append(
            CheckError(
                rule=CheckRule.COVERAGE,
                at="skipped",
                message="these lines hold content, so cite them instead of skipping"
                " them: " + "; ".join(f"{line.id} {line.text!r}" for line in content),
            )
        )
    dropped: list[str] = []
    for index, line in enumerate(lines):
        if line.id in reply.skipped:
            continue
        if line.id not in cited:
            dropped.append(f"{line.id} {line.text!r} (not cited)")
            continue
        missing: list[str] = []
        offset = 0
        for word in line.text.split():
            size = len(letters_and_digits(word))
            if size > configurations.max_joining_word_length and not any(
                used[index][offset : offset + size]
            ):
                missing.append(word)
            offset += size
        if missing:
            dropped.append(f"{line.id} {line.text!r} (unused: {' '.join(missing)})")
    if dropped:
        errors.append(
            CheckError(
                rule=CheckRule.COVERAGE,
                at="blocks",
                message="cite or skip each of these lines, and use all of a cited"
                " line's words: " + "; ".join(dropped),
            )
        )
    return errors
