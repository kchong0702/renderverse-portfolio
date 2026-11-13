from __future__ import annotations

from collections.abc import AsyncIterator
from functools import partial
from uuid import UUID

from pydantic import BaseModel, ValidationError

from src.clients.ezcareer import (
    Answer,
    Decision,
    Decisions,
    Published,
    ReviewRequired,
    RunEvent,
    RunMetadata,
)
from src.core.agent_runner import AgentRunner
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.core.logging import get_logger
from src.features.assistant.profile_edits import ProfileEdits
from src.features.assistant.schemas import (
    ChatMessage,
    ProfileApproval,
    ProfileDecision,
    ProfileSaved,
    UpdateProfileArgs,
)
from src.features.documents import ChangesetArtifact, DocumentService
from src.features.profile import ProfileService
from src.features.settings import SettingsService

_AGENT = "career-director"

logger = get_logger(__name__)


def _thread(user_id: UUID, chat_id: UUID) -> str:
    """The thread the chat runs on"""
    return f"{user_id}:{chat_id}"


class AssistantChat:
    def __init__(
        self,
        profile: ProfileService,
        settings: SettingsService,
        documents: DocumentService,
        edits: ProfileEdits,
        runner: AgentRunner,
    ):
        """Run career-director's turns through the runner, with the profile,
        settings, documents and profile edits a turn's events need"""
        self._profile = profile
        """The facts a turn starts with"""

        self._settings = settings
        """The run metadata each turn carries"""

        self._documents = documents
        """Where the changesets a turn proposes are stored"""

        self._edits = edits
        """The approval card for the profile changes a turn proposes"""

        self._runner = runner
        """What runs and streams each turn"""

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

    async def _turn(
        self,
        user_id: UUID,
        thread_id: str,
        metadata: RunMetadata | None,
        events: AsyncIterator[RunEvent[str]],
    ) -> AsyncIterator[BaseModel]:
        """A turn's events as the browser gets them: a changeset career-director
        publishes is stored and announced, saved profile changes are announced, a
        review of profile changes becomes a card or is rejected back to the model with
        why, and other published artifacts are not sent"""
        async for event in events:
            if isinstance(event, ReviewRequired):
                review = await self._review(user_id, event)
                if isinstance(review, ProfileApproval):
                    yield review
                    continue
                async for resumed in self._turn(
                    user_id,
                    thread_id,
                    metadata,
                    self._runner.answered(
                        user_id,
                        thread_id,
                        _AGENT,
                        str,
                        task_id=event.task_id,
                        answer=Decisions(
                            decisions=[Decision(type="reject", message=review)]
                            * len(event.actions)
                        ),
                        metadata=metadata,
                    ),
                ):
                    yield resumed
            elif not isinstance(event, Published):
                yield event
            elif event.name == "profile_updated":
                yield ProfileSaved.model_validate(event.data)
            elif event.name == "changeset":
                try:
                    artifact = ChangesetArtifact.model_validate(event.data)
                except ValidationError as error:
                    logger.warning("changeset_skipped", reason=str(error))
                    continue
                if proposed := await self._documents.propose_from_run(
                    user_id, artifact.document_id, artifact.changeset
                ):
                    yield proposed

    async def send(
        self, user_id: UUID, chat_id: UUID, message: ChatMessage
    ) -> AsyncIterator[str]:
        """Start a turn of the user's chat and return its events as they come; Conflict
        while a turn runs"""
        thread_id = _thread(user_id, chat_id)
        data = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        return await self._runner.start(
            user_id,
            thread_id,
            _AGENT,
            str,
            text=message.text,
            data=data,
            metadata=metadata,
            handle=partial(self._turn, user_id, thread_id, metadata),
        )

    async def answer(
        self, user_id: UUID, chat_id: UUID, task_id: str, answer: Answer | Decisions
    ) -> AsyncIterator[str]:
        """Answer the widget or tool call review a paused turn of the chat asked and
        return the rest of the turn's events as they come; Conflict while a turn runs"""
        thread_id = _thread(user_id, chat_id)
        metadata = await self._settings.run_metadata(user_id)
        return await self._runner.answer(
            user_id,
            thread_id,
            _AGENT,
            str,
            task_id=task_id,
            answer=answer,
            metadata=metadata,
            handle=partial(self._turn, user_id, thread_id, metadata),
        )

    async def decide(
        self, user_id: UUID, chat_id: UUID, task_id: str, decision: ProfileDecision
    ) -> AsyncIterator[str]:
        """Approve or cancel the profile changes a paused turn of the chat proposed
        and return the rest of the turn's events as they come"""
        return await self.answer(
            user_id,
            chat_id,
            task_id,
            Decisions(
                decisions=[
                    Decision(type="approve")
                    if decision.approve
                    else Decision(type="reject", message=decision.message)
                ]
            ),
        )

    async def resume(
        self, user_id: UUID, chat_id: UUID, last_event_id: str | None
    ) -> AsyncIterator[str]:
        """The chat's current turn after the Last-Event-ID the client last saw;
        NotFound when there is none to resume"""
        return await self._runner.resume(_thread(user_id, chat_id), last_event_id)

    async def cancel(self, user_id: UUID, chat_id: UUID, task_id: str) -> None:
        """Stop a running turn of one of the user's chats"""
        await self._runner.cancel(_AGENT, task_id, _thread(user_id, chat_id))


__all__ = ["AssistantChat"]
