import operator
from dataclasses import dataclass
from typing import Annotated, Any, TypedDict

from langchain_core.language_models import BaseChatModel

from src.features.import_document.config import ImportConfig
from src.shared.checks import CheckError
from src.shared.extraction import Line


@dataclass(frozen=True)
class ImportContext:
    config: ImportConfig
    """Prompt, model and limits the run uses"""

    model: BaseChatModel
    """Chat model named by the config"""


class ImportState(TypedDict, total=False):
    file: bytes
    """The uploaded PDF or Word file"""

    lines: list[Line]
    """The file's text lines, returned so ops can keep them with the upload"""

    reply: dict[str, Any]
    """The LLM's last ResumeImport, as it sent it"""

    fix_summary: str
    """What the last reply got wrong, written for the LLM"""

    rounds: Annotated[list[list[CheckError]], operator.add]
    """The verifier's errors for each reply, empty for the one that passed"""
