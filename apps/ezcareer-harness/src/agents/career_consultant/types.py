from document_schema import AnyDocument
from pydantic import BaseModel, ConfigDict

from src.shared.extraction.types import Line


class ChangesetProposed(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    changeset_id: str
    """The id ops-api saved the proposed changeset under"""


class DocumentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    title: str
    """The document's title, such as Backend résumé"""

    document: AnyDocument
    """The document's current draft"""

    pdf_lines: list[Line]
    """The uploaded PDF's lines; empty for a document not imported from a PDF"""

    job_id: str | None
    """The job the document is a copy for; None for one not a job's"""


class JobRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    text: str
    """What the posting asks for; untrusted"""

    importance: str
    """How much it matters, such as required or nice_to_have"""

    match: str
    """How well the profile meets it, such as met or partly_met"""

    reason: str
    """Why it matches as it does"""


class TargetJob(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    title: str
    """The job title"""

    company: str
    """The employer"""

    location: str
    """Where the job is"""

    url: str
    """Where the posting is"""

    requirements: list[JobRequirement]
    """What the posting asks for, as its analysis found; empty before an analysis"""


class CopiedForJob(DocumentDraft):
    document_id: str
    """The copy's id, which the agent works on from then on"""

    job: TargetJob
    """The job the copy is for"""

    rejected_changeset: bool
    """Whether starting over rejected the copy's pending changeset"""
