import re
from collections.abc import Iterator, Mapping

from document_schema import AnyDocument, Changeset, RichValue, Value, apply_edits

from src.shared.checks import CheckError


def _values(node: object, at: str) -> Iterator[tuple[str, Value | RichValue]]:
    """Every Value and RichValue in an edit's JSON, with where it is"""
    match node:
        case {"src": list(), "text": str()}:
            yield at, Value.model_validate(node)
        case {"src": list(), "html": str()}:
            yield at, RichValue.model_validate(node)
        case dict():
            for key, child in node.items():
                yield from _values(child, f"{at}/{key}")
        case list():
            for index, child in enumerate(node):
                yield from _values(child, f"{at}/{index}")


def _words(text: str) -> list[str]:
    """The text's words, without punctuation"""
    return re.findall(r"[\w+#'-]+", text)


def _claims(text: str, prose: bool) -> set[str]:
    """Numbers and names: words with a digit or a capital, skipping the
    first word of each sentence in prose"""
    names = [
        word
        for sentence in re.split(r"[.!?:;]\s+", text)
        for word in _words(sentence)[1 if prose else 0 :]
        if word[0].isupper()
    ]
    numbers = [word for word in _words(text) if any(c.isdigit() for c in word)]
    return {word.casefold() for word in names + numbers}


def _locked(document: AnyDocument) -> dict[str, object]:
    """The parts only the user changes: the photo and the letter's signature"""
    return {
        block.id: block if block.kind == "photo" else block.signature
        for block in document.content.blocks
        if block.kind in ("photo", "letter")
    }


def check_changeset(
    document: AnyDocument, changeset: Changeset, sources: Mapping[str, str]
) -> list[CheckError]:
    """Errors in a proposed changeset, empty when it can go to the user
    sources maps each PDF line id and fact:<id> to its text"""
    try:
        edited = apply_edits(document, changeset.edits)
    except ValueError as error:
        return [CheckError(rule="not_applicable", at="edits", message=str(error))]
    errors: list[CheckError] = []
    if _locked(edited) != _locked(document):
        errors.append(
            CheckError(
                rule="locked",
                at="edits",
                message="only the user changes, hides or removes the photo or the signature",
            )
        )
    for index, edit in enumerate(changeset.edits):
        for at, value in _values(edit.model_dump(mode="json"), f"edits/{index}"):
            if not value.src:
                rule, message = "uncited", f"{value.text!r} cites nothing"
            elif unknown := [s for s in value.src if s not in sources]:
                rule = "unknown_source"
                message = f"{', '.join(unknown)} are not PDF lines or facts"
            elif missing := _claims(value.text, isinstance(value, RichValue)) - {
                word.casefold() for s in value.src for word in _words(sources[s])
            }:
                rule = "unsupported"
                message = (
                    f"{', '.join(sorted(missing))} in {value.text!r} are not in"
                    f" {', '.join(value.src)}; cite a fact that says it or leave it out"
                )
            else:
                continue
            errors.append(CheckError(rule=rule, at=at, message=message))
    return errors


CHECKS = {"changeset": check_changeset}
"""Every check the write-document configurations.yaml may turn on, by name"""
