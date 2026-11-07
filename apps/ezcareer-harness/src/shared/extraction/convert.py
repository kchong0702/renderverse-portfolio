import io
import subprocess
import tempfile
import zipfile
from pathlib import Path

from src.shared.extraction.errors import UnreadableFile


def to_pdf(file: bytes, soffice: str = "soffice") -> bytes:
    """Returns a PDF as it is and converts a Word file with LibreOffice"""
    if file.startswith(b"%PDF"):
        return file
    try:
        is_word = "word/document.xml" in zipfile.ZipFile(io.BytesIO(file)).namelist()
    except zipfile.BadZipFile:
        is_word = False
    if not is_word:
        raise UnreadableFile("upload a PDF or a Word (.docx) file")
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "resume.docx"
        source.write_bytes(file)
        try:
            subprocess.run(
                [
                    soffice,
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
                timeout=60,
            )
            return source.with_suffix(".pdf").read_bytes()
        except (OSError, subprocess.SubprocessError) as error:
            raise UnreadableFile(
                "the Word file could not be converted to PDF"
            ) from error
