from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import suppress
from functools import partial
from uuid import UUID

from document_schema import ChangesetStatus
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import Answer, Published, RunEvent
from src.core.agent_runner import AgentRunner
from src.core.exceptions import Conflict
from src.core.logging import get_logger
from src.features.documents.models import Document
from src.features.documents.schemas import (
    ChangesetArtifact,
    EditDocumentInput,
    TailoredDocument,
)
from src.features.documents.service import DocumentService
from src.features.profile import ProfileService
from src.features.settings import SettingsService

_AGENT = "career-consultant"

logger = get_logger(__name__)


def _thread(user_id: UUID, document_id: UUID) -> str:
    """The thread the document's chat runs on"""
    return f"{user_id}:document:{document_id}"


class DocumentChat:
    def __init__(
        self,
        session: AsyncSession,
        documents: DocumentService,
        profile: ProfileService,
        settings: SettingsService,
        runner: AgentRunner,
    ):
        """Run career-consultant's turns on the user's documents, committing the session
        first so the changesets a run stores on another session see its writes"""
        self._session = session
        """The request's session, committed before each turn"""

        self._documents = documents
        """The user's documents and the changesets a turn proposes"""

        self._profile = profile
        """The facts a turn starts with"""

        self._settings = settings
        """The run metadata each turn carries"""

        self._runner = runner
        """What runs and streams each turn"""

    async def _events(
        self,
        user_id: UUID,
        document_id: UUID,
        events: AsyncIterator[RunEvent[str]],
    ) -> AsyncIterator[BaseModel]:
        """A turn's events as the browser gets them: a changeset career-consultant
        publishes for the document is stored and announced, and other published
        artifacts are not sent"""
        async for event in events:
            if not isinstance(event, Published):
                yield event
            elif event.name == "changeset":
                try:
                    artifact = ChangesetArtifact.model_validate(event.data)
                except ValidationError as error:
                    logger.warning("changeset_skipped", reason=str(error))
                    continue
                if artifact.document_id == document_id and (
                    proposed := await self._documents.propose_from_run(
                        user_id, document_id, artifact.changeset
                    )
                ):
                    yield proposed

    async def send(
        self, user_id: UUID, document_id: UUID, text: str
    ) -> AsyncIterator[str]:
        """Start a turn of the document's chat on its current draft and lines and return
        its events as they come; Conflict while a turn runs"""
        document, lines = await self._documents.content(user_id, document_id)
        data = EditDocumentInput(
            document_id=document_id,
            document=document,
            lines=lines,
            facts=(await self._profile.agent_profile(user_id)).facts,
        )
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return await self._runner.start(
            user_id,
            _thread(user_id, document_id),
            _AGENT,
            str,
            text=text,
            data=data,
            metadata=metadata,
            handle=partial(self._events, user_id, document_id),
        )

    async def answer(
        self, user_id: UUID, document_id: UUID, task_id: str, answer: Answer
    ) -> AsyncIterator[str]:
        """Answer the widget a paused turn of the document's chat asked and return the
        rest of the turn's events as they come; Conflict while a turn runs"""
        await self._documents.require(user_id, document_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return await self._runner.answer(
            user_id,
            _thread(user_id, document_id),
            _AGENT,
            str,
            task_id=task_id,
            answer=answer,
            metadata=metadata,
            handle=partial(self._events, user_id, document_id),
        )

    async def resume(
        self, user_id: UUID, document_id: UUID, last_event_id: str | None
    ) -> AsyncIterator[str]:
        """The document chat's current turn after the Last-Event-ID the client last
        saw; NotFound when there is none to resume"""
        return await self._runner.resume(_thread(user_id, document_id), last_event_id)

    async def cancel(self, user_id: UUID, document_id: UUID, task_id: str) -> None:
        """Stop the running turn of the document's chat"""
        await self._runner.cancel(_AGENT, task_id, _thread(user_id, document_id))

    async def tailor(
        self, user_id: UUID, document: Document, text: str
    ) -> TailoredDocument:
        """Start the copy's chat turn on text unless a changeset still waits for the
        user; a turn already running carries on"""
        waiting = any(
            row.changeset.status is ChangesetStatus.PENDING
            for row in await self._documents.changesets(user_id, document.id)
        )
        if not waiting:
            with suppress(Conflict):
                await self.send(user_id, document.id, text)
        return TailoredDocument(document_id=document.id, tailoring=not waiting)


__all__ = ["DocumentChat"]
