from __future__ import annotations

import csv
import io
import zipfile
from pathlib import PurePosixPath

from src.features.profile.exceptions import UnreadableExport
from src.features.profile.schemas import ExportFile, ProfileExport

_FOR_HARNESS = {
    "profile.csv",
    "profile summary.csv",
    "positions.csv",
    "education.csv",
    "projects.csv",
    "skills.csv",
}

_CONTACTS = {"email addresses.csv", "phonenumbers.csv"}


def read_export(data: bytes, max_unzipped_bytes: int) -> ProfileExport:
    """The profile, job, education, project and skill files of an export zip for
    import-profile, and its name, email and phone; every other file is ignored"""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise UnreadableExport("The file is not a zip archive") from error
    with archive:
        members = {
            PurePosixPath(info.filename).name: info
            for info in archive.infolist()
            if not info.is_dir()
            and PurePosixPath(info.filename).name.lower() in _FOR_HARNESS | _CONTACTS
        }
        if not any(name.lower() in _FOR_HARNESS for name in members):
            raise UnreadableExport("The zip has no profile, job or skill files")
        if sum(info.file_size for info in members.values()) > max_unzipped_bytes:
            raise UnreadableExport("The export's profile files are unexpectedly large")
        rows = {
            name: [
                {
                    (key or "").strip(): (value or "").strip()
                    for key, value in row.items()
                }
                for row in csv.DictReader(
                    io.StringIO(
                        archive.read(info).decode("utf-8-sig", errors="replace")
                    )
                )
            ]
            for name, info in members.items()
        }
    lowered = {name.lower(): table for name, table in rows.items()}
    profile = (lowered.get("profile.csv") or [{}])[0]
    emails = lowered.get("email addresses.csv", [])
    return ProfileExport(
        files=[
            ExportFile(name=name, rows=table)
            for name, table in rows.items()
            if name.lower() in _FOR_HARNESS
        ],
        name=" ".join(
            part
            for part in (profile.get("First Name"), profile.get("Last Name"))
            if part
        ),
        email=next(
            (
                row.get("Email Address", "")
                for row in emails
                if row.get("Primary") == "Yes"
            ),
            emails[0].get("Email Address", "") if emails else "",
        ),
        phone=next(
            (
                row["Number"]
                for row in lowered.get("phonenumbers.csv", [])
                if row.get("Number")
            ),
            "",
        ),
    )


__all__ = ["read_export"]
