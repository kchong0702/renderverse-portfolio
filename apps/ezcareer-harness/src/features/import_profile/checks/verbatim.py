from src.features.import_profile.schemas import ExportFile, ImportedProfile
from src.shared.checks import CheckError, CheckRule


def _plain(text: str) -> str:
    """The text case folded, with its spacing collapsed and its edge punctuation and
    list markers dropped"""
    return " ".join(text.split()).strip(" .,;:•·*–—-").casefold()


def check_verbatim(reply: ImportedProfile, files: list[ExportFile]) -> list[CheckError]:
    """Errors for each copied value not word for word in the export, and each entry
    value, highlight or date's year not in a row holding the entry's title"""
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
    errors = [
        CheckError(
            rule=CheckRule.VERBATIM,
            at=at,
            message=f"{value!r} is not word for word in the export",
        )
        for at, value in copied
        if not any(_plain(value) in row for row in rows)
    ]
    for index, entry in enumerate(reply.entries):
        at = f"entries/{index}"
        if not (sources := [row for row in rows if _plain(entry.title) in row]):
            errors.append(
                CheckError(
                    rule=CheckRule.VERBATIM,
                    at=f"{at}/title",
                    message=f"{entry.title!r} is not word for word in the export",
                )
            )
            continue
        values = [
            *(
                (name, value)
                for name in ("organisation", "location", "summary", "link", "code_link")
                if (value := getattr(entry, name))
            ),
            *(
                (name, value[:4])
                for name in ("start", "end")
                if (value := getattr(entry, name)) and value != "present"
            ),
            *((f"highlights/{i}", value) for i, value in enumerate(entry.highlights)),
            *((f"tools/{i}", value) for i, value in enumerate(entry.tools)),
        ]
        errors.extend(
            CheckError(
                rule=CheckRule.VERBATIM,
                at=f"{at}/{name}",
                message=f"{value!r} is not word for word in the row of"
                f" {entry.title!r}; copy it from that row",
            )
            for name, value in values
            if not any(_plain(value) in row for row in sources)
        )
    return errors
