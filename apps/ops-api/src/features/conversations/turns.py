from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from pydantic import BaseModel, JsonValue, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.ezcareer import (
    Cancelled,
    Completed,
    Decision,
    Decisions,
    Failed,
    InputRequired,
    Published,
    Replied,
    ReviewRequired,
    RunEvent,
    RunMetadata,
    Step,
    StepUpdate,
)
from src.core.agent_runner import AgentRunner, Turn
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.core.logging import get_logger
from src.features.assistant.profile_edits import ProfileEdits
from src.features.assistant.schemas import (
    ProfileApproval,
    ProfileSaved,
    UpdateProfileArgs,
)
from src.features.conversations.enums import MessageRole, ServedAgent
from src.features.conversations.models import (
    AgentThread,
    ThreadMessage,
    ThreadMessageChangeset,
)
from src.features.documents import ChangesetArtifact, ChangesetProposed
from src.features.documents.models import Document
from src.features.documents.repository import DocumentRepository

logger = get_logger(__name__)


class ConversationTurns:
    def __init__(self, factory: async_sessionmaker[AsyncSession], runner: AgentRunner):
        """Rewrite agent turns' events for the browser and keep each turn's answer, on
        sessions of their own since a turn outlives its request"""
        self._factory = factory
        """Sessions for the answers, changesets and profile edits a turn reads"""

        self._runner = runner
        """What continues a turn after a review is rejected back to the model"""

        self._edits = ProfileEdits(factory)
        """The approval card for the profile changes a turn proposes"""

    def turn(
        self,
        user_id: UUID,
        thread_id: UUID,
        agent: ServedAgent,
        metadata: RunMetadata | None,
    ) -> Turn:
        """A turn of the user's thread with its session's agent, its messages carrying
        the user's model"""
        return Turn(
            user_id=user_id,
            thread_id=str(thread_id),
            agent=agent.value,
            metadata=metadata,
            handle=self._handle,
        )

    async def _review(
        self, user_id: UUID, review: ReviewRequired
    ) -> ProfileApproval | str:
        """The card for the one update_profile call a turn paused on, or why it can't
        be shown"""
        if [action.name for action in review.actions] != ["update_profile"]:
            return "Propose all changes in one update_profile call"
        try:
            return await self._edits.approval(
                user_id,
                review.task_id,
                UpdateProfileArgs.model_validate(review.actions[0].args),
            )
        except (ValidationError, NotFound, InvalidInput, Conflict) as error:
            return str(error)

    async def _changeset(
        self, user_id: UUID, data: JsonValue
    ) -> ChangesetProposed | None:
        """The changeset a turn published as stored, for the browser; None, logged,
        when it names no changeset of the user's"""
        try:
            artifact = ChangesetArtifact.model_validate(data)
        except ValidationError as error:
            logger.warning("changeset_skipped", reason=str(error))
            return None
        async with self._factory() as session:
            repository = DocumentRepository(session)
            document = await repository.owned(Document, user_id, artifact.document_id)
            row = (
                await repository.changeset(document.id, artifact.changeset_id)
                if document
                else None
            )
        if document is None or row is None:
            logger.warning("changeset_skipped", reason="No such changeset")
            return None
        return ChangesetProposed(
            document_id=document.id, changeset_id=row.id, created_at=row.created_at
        )

    async def _answered(
        self,
        turn: Turn,
        run_id: str,
        replied: Replied | None,
        ended: BaseModel,
        steps: dict[str, Step],
        changesets: list[UUID],
    ) -> None:
        """Keep how the run ended as the agent's message, once even after a
        reconnect"""
        match ended:
            case Completed(reply=reply):
                text, failure = str(reply), None
            case InputRequired(widget=widget):
                text, failure = widget.label or "", None
            case Failed(reason=reason):
                text, failure = "", reason
            case Cancelled():
                text, failure = "", "You stopped this reply."
            case _:
                text, failure = "", None
        async with self._factory() as session, session.begin():
            thread_document = await session.scalar(
                select(AgentThread.document_id).where(
                    AgentThread.id == UUID(turn.thread_id)
                )
            )
            message_id = replied.message_id if replied else f"run-{run_id}"
            row = await session.get(ThreadMessage, message_id)
            if row is None and replied:
                row = await session.get(ThreadMessage, f"run-{run_id}")
                if row:
                    row.id = message_id
            if row is None:
                row = ThreadMessage(
                    id=message_id,
                    user_id=turn.user_id,
                    thread_id=UUID(turn.thread_id),
                    role=MessageRole.AGENT,
                    agent=turn.agent,
                    document_id=thread_document,
                )
                session.add(row)
            row.text = text
            row.steps = list(steps.values()) or row.steps or []
            kept = {changeset.id for changeset in row.changesets}
            session.add_all(
                ThreadMessageChangeset(
                    user_id=turn.user_id, message_id=row.id, changeset_id=changeset_id
                )
                for changeset_id in changesets
                if changeset_id not in kept
            )
            row.failure = failure

    async def _rewrite(
        self,
        turn: Turn,
        run_id: str,
        events: AsyncIterator[RunEvent[str]],
        steps: dict[str, Step],
        changesets: list[UUID],
    ) -> AsyncIterator[BaseModel]:
        """A turn's events as the browser gets them, keeping the turn's answer as a
        message when it ends; steps and changesets keep what it ran and proposed"""
        replied = None
        async for event in events:
            match event:
                case Replied():
                    replied = event
                case StepUpdate():
                    steps[event.step.id] = event.step
                    yield event
                case ReviewRequired():
                    review = await self._review(turn.user_id, event)
                    if isinstance(review, ProfileApproval):
                        await self._answered(
                            turn,
                            run_id,
                            replied,
                            review,
                            steps,
                            changesets,
                        )
                        yield review
                        continue
                    async for resumed in self._rewrite(
                        turn,
                        run_id,
                        self._runner.answered(
                            turn,
                            run_id,
                            event.task_id,
                            Decisions(
                                decisions=[Decision(type="reject", message=review)]
                                * len(event.actions)
                            ),
                        ),
                        steps,
                        changesets,
                    ):
                        yield resumed
                case Published(name="profile_updated"):
                    yield ProfileSaved.model_validate(event.data)
                case Published(name="changeset"):
                    proposed = await self._changeset(turn.user_id, event.data)
                    if proposed and proposed.changeset_id not in changesets:
                        changesets.append(proposed.changeset_id)
                        yield proposed
                case Published():
                    pass
                case Completed() | InputRequired() | Failed() | Cancelled():
                    await self._answered(
                        turn,
                        run_id,
                        replied,
                        event,
                        steps,
                        changesets,
                    )
                    yield event
                case _:
                    yield event

    def _handle(
        self, turn: Turn, run_id: str, events: AsyncIterator[RunEvent[str]]
    ) -> AsyncIterator[BaseModel]:
        """A run's events rewritten for the browser, its answer kept as a message"""
        return self._rewrite(turn, run_id, events, {}, [])


__all__ = ["ConversationTurns"]
