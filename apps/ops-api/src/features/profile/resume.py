from __future__ import annotations

from document_schema import (
    ContactKind,
    Contacts,
    Education,
    Entry,
    Experience,
    Languages,
    Project,
    Projects,
    ResumeContent,
    Skills,
    Summary,
)
from document_schema import Profile as NameBlock

from src.features.profile.enums import EntryKind
from src.features.profile.schemas import (
    ImportedAbout,
    ImportedEntry,
    ImportedProfile,
    ImportedSkill,
    ProfileLink,
)

_LINK_LABELS = {
    ContactKind.LINKEDIN: "LinkedIn",
    ContactKind.GITHUB: "GitHub",
    ContactKind.WEBSITE: "Website",
    ContactKind.OTHER: "Link",
}


def _highlights(entry: Entry) -> list[str]:
    """The entry's bullets as plain sentences"""
    return [text for bullet in entry.bullets if (text := bullet.text.text.strip())]


def _project(project: Project) -> ImportedEntry:
    """A project, its GitHub or GitLab link as the code link and the first other
    link as the live one"""
    urls = [link.url.text for link in project.links]
    code = [url for url in urls if "github" in url or "gitlab" in url]
    live = [url for url in urls if url not in code]
    return ImportedEntry(
        kind=EntryKind.PROJECT,
        title=project.name.text,
        start=project.dates.start if project.dates else None,
        end=project.dates.end if project.dates else None,
        summary=project.description.text if project.description else "",
        highlights=_highlights(project),
        link=live[0] if live else None,
        code_link=code[0] if code else None,
        tools=[tag.text.text for tag in project.tags if 0 < len(tag.text.text) <= 50][
            :20
        ],
    )


def _about(content: ResumeContent) -> ImportedAbout:
    """The name, headline, contacts and summary the résumé gives"""
    about: dict[str, str] = {}
    links: list[ProfileLink] = []
    for block in content.blocks:
        match block:
            case NameBlock(name=name, headline=headline):
                about["name"] = name.text
                about["headline"] = headline.text if headline else ""
            case Summary(text=text):
                about["summary"] = text.text
            case Contacts(items=items):
                for contact in items:
                    value = contact.value.text
                    if contact.kind in _LINK_LABELS:
                        links.append(
                            ProfileLink(
                                label=(contact.label.text[:40] if contact.label else "")
                                or _LINK_LABELS[contact.kind],
                                url=value
                                if value.startswith(("http://", "https://"))
                                else f"https://{value}",
                            )
                        )
                    else:
                        about.setdefault(contact.kind.value, value)
            case _:
                pass
    return ImportedAbout(**about, links=links)


def resume_profile(content: ResumeContent) -> ImportedProfile:
    """A résumé's details, jobs, degrees, projects, skills and languages as an
    imported profile; every other section is dropped"""
    entries: list[ImportedEntry] = []
    skills: list[ImportedSkill] = []
    for block in content.blocks:
        match block:
            case Experience(items=jobs):
                entries += [
                    ImportedEntry(
                        kind=EntryKind.ROLE,
                        title=job.role.text,
                        organisation=job.company.text,
                        location=job.location.text if job.location else "",
                        start=job.dates.start if job.dates else None,
                        end=job.dates.end if job.dates else None,
                        summary=job.description.text if job.description else "",
                        highlights=_highlights(job),
                    )
                    for job in jobs
                    if job.role.text.strip()
                ]
            case Education(items=degrees):
                entries += [
                    ImportedEntry(
                        kind=EntryKind.EDUCATION,
                        title=degree.degree.text,
                        organisation=degree.school.text,
                        location=degree.location.text if degree.location else "",
                        start=degree.dates.start if degree.dates else None,
                        end=degree.dates.end if degree.dates else None,
                        summary=degree.grade.text if degree.grade else "",
                        highlights=_highlights(degree),
                    )
                    for degree in degrees
                    if degree.degree.text.strip()
                ]
            case Projects(items=projects):
                entries += [
                    _project(project)
                    for project in projects
                    if project.name.text.strip()
                ]
            case Skills(items=rows):
                skills += [
                    ImportedSkill(
                        name=item.text.text, group=row.label.text if row.label else ""
                    )
                    for row in rows
                    for item in row.items
                    if item.text.text.strip()
                ]
            case Languages(items=languages):
                skills += [
                    ImportedSkill(name=language.language.text, group="Spoken languages")
                    for language in languages
                    if language.language.text.strip()
                ]
            case _:
                pass
    return ImportedProfile(about=_about(content), entries=entries, skills=skills)


__all__ = ["resume_profile"]
