import subprocess
import tempfile
import threading
from pathlib import Path

import filetype

from src.core.config import get_settings
from src.features.convert_document.exceptions import UnconvertibleFile

_settings = get_settings()
_slots = threading.BoundedSemaphore(_settings.libreoffice.max_concurrent_conversions)


def convert_document(file: bytes) -> bytes:
    """Returns a PDF as it is and converts a Word file with LibreOffice, waiting
    for a free slot"""
    kind = filetype.guess_extension(file)
    if kind == "pdf":
        return file
    if kind != "docx":
        raise UnconvertibleFile("upload a PDF or a Word (.docx) file")
    with _slots, tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "resume.docx"
        source.write_bytes(file)
        try:
            subprocess.run(
                [
                    _settings.libreoffice.command,
                    f"-env:UserInstallation={Path(folder).as_uri()}/profile",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    folder,
                    str(source),
                ],
                check=True,
                capture_output=True,
                timeout=_settings.libreoffice.timeout_s,
            )
            return source.with_suffix(".pdf").read_bytes()
        except (OSError, subprocess.SubprocessError) as error:
            raise UnconvertibleFile(
                "the Word file could not be converted to PDF"
            ) from error
