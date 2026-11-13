from src.features.import_profile.schemas import ExportFile, ImportedProfile
from src.shared.checks import CheckError, CheckRule


def _plain(text: str) -> str:
    """The text case folded, with its spacing collapsed and its edge punctuation and
    list markers dropped"""
    return " ".join(text.split()).strip(" .,;:•·*–—-").casefold()


def check_verbatim(reply: ImportedProfile, files: list[ExportFile]) -> list[CheckError]:
    """Errors for each copied value not word for word in the export"""
    rows = [_plain("\n".join(row.values())) for file in files for row in file.rows]
    about = reply.about
    copied = [
        *(
            (f"about/{name}", value)
            for name in ("headline", "summary", "location")
            if (value := getattr(about, name))
        ),
        *((f"about/links/{i}/url", link.url) for i, link in enumerate(about.links)),
        *((f"skills/{i}/name", skill.name) for i, skill in enumerate(reply.skills)),
    ]
    for index, entry in enumerate(reply.entries):
        at = f"entries/{index}"
        copied.extend(
            (f"{at}/{name}", value)
            for name in (
                "title",
                "organisation",
                "location",
                "summary",
                "link",
                "code_link",
            )
            if (value := getattr(entry, name))
        )
        copied.extend(
            (f"{at}/highlights/{i}", value) for i, value in enumerate(entry.highlights)
        )
        copied.extend((f"{at}/tools/{i}", value) for i, value in enumerate(entry.tools))
    return [
        CheckError(
            rule=CheckRule.VERBATIM,
            at=at,
            message=f"{value!r} is not word for word in the export",
        )
        for at, value in copied
        if not any(_plain(value) in row for row in rows)
    ]
