from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

from document_schema import ChangesetStatus
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import (
    Answer,
    Decision,
    Decisions,
    MessageMetadata,
    SummaryUpdate,
    ThreadSummary,
)
from src.core.agent_runner import AgentRunner
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.db.base import utcnow
from src.features.assistant.schemas import ProfileDecision
from src.features.conversations.enums import MessageRole, ServedAgent
from src.features.conversations.models import AgentSession, AgentThread, ThreadMessage
from src.features.conversations.repository import ConversationRepository
from src.features.conversations.schemas import (
    ConsultantInput,
    MessagePage,
    SessionRead,
    SkippedTurn,
    StartedTurn,
    ThreadMessageRead,
)
from src.features.conversations.turns import ConversationTurns
from src.features.documents import DocumentService
from src.features.documents.models import Document
from src.features.profile import ProfileService
from src.features.settings import SettingsService


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        turns: ConversationTurns,
        runner: AgentRunner,
        documents: DocumentService,
        profile: ProfileService,
        settings: SettingsService,
    ):
        """Hold the request's session, its repository, the turns, the runner and the
        services a turn's input and metadata come from"""
        self._session = session
        self._repository = ConversationRepository(session)
        self._turns = turns
        self._runner = runner
        self._documents = documents
        self._profile = profile
        self._settings = settings

    async def _thread(
        self, user_id: UUID, thread_id: UUID, *, writing: bool = False
    ) -> tuple[ServedAgent, UUID | None]:
        """The agent of the user's thread's session and the thread's document;
        NotFound when it is not theirs, Conflict when writing to it once cleared"""
        found = await self._repository.thread(user_id, thread_id)
        if found is None:
            raise NotFound("No such thread")
        agent, document_id, cleared = found
        if writing and cleared:
            raise Conflict("This conversation was cleared and a new one started")
        return agent, document_id

    async def _agent_session(self, user_id: UUID, agent: ServedAgent) -> AgentSession:
        """The user's session with the agent; NotFound before sign-in made it"""
        row = await self._repository.session(user_id, agent)
        if row is None:
            raise NotFound("Sign in again to talk to this agent")
        return row

    async def _document_thread(self, user_id: UUID, document_id: UUID) -> AgentThread:
        """The active career-consultant thread on the user's document, made the first
        time; NotFound when the document is not theirs"""
        await self._documents.require(user_id, document_id)
        return await self._repository.document_thread(
            await self._agent_session(user_id, ServedAgent.CAREER_CONSULTANT),
            document_id,
        )

    async def session(
        self, user_id: UUID, agent: ServedAgent, document_id: UUID | None
    ) -> SessionRead:
        """The user's conversation with the agent and its active thread, the
        document's for career-consultant"""
        match agent, document_id:
            case ServedAgent.CAREER_DIRECTOR, None:
                row = await self._agent_session(user_id, agent)
                thread_id = row.active_thread_id
            case ServedAgent.CAREER_CONSULTANT, UUID() as document_id:
                thread_id = (await self._document_thread(user_id, document_id)).id
            case ServedAgent.CAREER_DIRECTOR, _:
                raise InvalidInput(
                    "career-director's conversation is about no document"
                )
            case _:
                raise InvalidInput("Say which document the conversation is about")
        if thread_id is None:
            raise NotFound("Sign in again to talk to this agent")
        return SessionRead(agent=agent, thread_id=thread_id)

    async def clear(
        self, user_id: UUID, agent: ServedAgent, document_id: UUID | None
    ) -> SessionRead:
        """Clear the conversation the agent's session holds, the document's for
        career-consultant: new turns go on a new thread"""
        current = await self.session(user_id, agent, document_id)
        thread = await self._repository.replace(current.thread_id)
        if agent is ServedAgent.CAREER_DIRECTOR:
            (await self._agent_session(user_id, agent)).active_thread_id = thread.id
        return SessionRead(agent=agent, thread_id=thread.id)

    async def messages(
        self, user_id: UUID, thread_id: UUID, before: str | None, limit: int
    ) -> MessagePage:
        """Up to limit of the thread's messages before the message `before`, or its
        latest, oldest first"""
        await self._thread(user_id, thread_id)
        seen = await self._repository.message(thread_id, before) if before else None
        if before and seen is None:
            raise NotFound("No such message")
        rows = await self._repository.page(thread_id, seen, limit + 1)
        return MessagePage(
            messages=[ThreadMessageRead.model_validate(r) for r in rows[:limit][::-1]],
            has_more=len(rows) > limit,
        )

    async def send(
        self, user_id: UUID, thread_id: UUID, text: str, timezone: str
    ) -> AsyncIterator[str]:
        """Save the user's message and start a turn on it, or answer the pause the last
        turn ended on; Conflict while a turn runs"""
        agent, document_id = await self._thread(user_id, thread_id, writing=True)
        if paused := await self._runner.paused(str(thread_id)):
            task_id, asked = paused
            return await self.answer(
                user_id,
                thread_id,
                task_id,
                Decisions(decisions=[Decision(type="reject", message=text)])
                if asked == "profile_approval"
                else Answer(input=text, accept=True),
                text,
                timezone,
            )
        profile = await self._profile.agent_profile(user_id)
        match agent, document_id:
            case ServedAgent.CAREER_CONSULTANT, UUID() as document_id:
                data: BaseModel = ConsultantInput(
                    profile_facts=profile.profile_facts,
                    preferences=profile.preferences,
                    desired_document_id=document_id,
                )
            case ServedAgent.CAREER_DIRECTOR, None:
                data = profile
            case _:
                raise NotFound("No such thread")
        metadata = await self._settings.run_metadata(user_id)
        message_id = uuid4().hex
        created_at = utcnow()

        async def save() -> None:
            """Commit the user's message before the turn starts"""
            await self._repository.add(
                ThreadMessage(
                    id=message_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    role=MessageRole.USER,
                    text=text,
                    timezone=timezone,
                    document_id=document_id,
                    created_at=created_at,
                )
            )
            await self._session.commit()

        return await self._runner.start(
            self._turns.turn(user_id, thread_id, agent, metadata),
            message_id=message_id,
            text=text,
            sent=MessageMetadata(created_at=created_at, timezone=timezone),
            data=data,
            prepare=save,
        )

    async def answer(
        self,
        user_id: UUID,
        thread_id: UUID,
        task_id: str,
        answer: Answer | Decisions,
        text: str,
        timezone: str,
    ) -> AsyncIterator[str]:
        """Save the user's answer as text and send it to the turn paused on task_id;
        Conflict while a turn runs"""
        agent, document_id = await self._thread(user_id, thread_id, writing=True)
        metadata = await self._settings.run_metadata(user_id)

        async def save() -> None:
            """Commit the user's answer before the turn resumes"""
            await self._repository.add(
                ThreadMessage(
                    id=uuid4().hex,
                    user_id=user_id,
                    thread_id=thread_id,
                    role=MessageRole.USER,
                    text=text,
                    timezone=timezone,
                    document_id=document_id,
                )
            )
            await self._session.commit()

        return await self._runner.answer(
            self._turns.turn(user_id, thread_id, agent, metadata),
            task_id=task_id,
            answer=answer,
            prepare=save,
        )

    async def decide(
        self,
        user_id: UUID,
        thread_id: UUID,
        task_id: str,
        decision: ProfileDecision,
        timezone: str,
    ) -> AsyncIterator[str]:
        """Approve or cancel the profile changes a paused turn proposed and return the
        rest of its events as they come"""
        return await self.answer(
            user_id,
            thread_id,
            task_id,
            Decisions(
                decisions=[
                    Decision(type="approve")
                    if decision.approve
                    else Decision(type="reject", message=decision.message)
                ]
            ),
            "Approved" if decision.approve else decision.message or "Declined",
            timezone,
        )

    async def resume(
        self, user_id: UUID, thread_id: UUID, last_event_id: str | None
    ) -> AsyncIterator[str]:
        """The thread's current turn after the Last-Event-ID the client last saw;
        NotFound when there is none to resume"""
        await self._thread(user_id, thread_id)
        return await self._runner.resume(str(thread_id), last_event_id)

    async def cancel(self, user_id: UUID, thread_id: UUID, task_id: str) -> None:
        """Stop the thread's running turn"""
        agent, _ = await self._thread(user_id, thread_id)
        await self._runner.cancel(agent.value, task_id, str(thread_id))

    async def summary(self, user_id: UUID, thread_id: UUID) -> ThreadSummary:
        """What the thread's agent remembers of its earlier messages"""
        agent, _ = await self._thread(user_id, thread_id)
        return await self._runner.summary(str(thread_id), agent.value)

    async def update_summary(
        self, user_id: UUID, thread_id: UUID, update: SummaryUpdate
    ) -> ThreadSummary:
        """Replace the thread's summary with the user's edit"""
        agent, _ = await self._thread(user_id, thread_id)
        return await self._runner.update_summary(str(thread_id), agent.value, update)

    async def edit(
        self, user_id: UUID, document: Document, text: str, timezone: str
    ) -> StartedTurn | SkippedTurn:
        """Start a turn of the document's career-consultant thread on text, or say why
        not: a changeset waits, or the thread is busy or waits on the user"""
        if any(
            row.changeset.status is ChangesetStatus.PENDING
            for row in await self._documents.changesets(user_id, document.id)
        ):
            return SkippedTurn(
                document_id=document.id, reason="Its proposed edits wait for review"
            )
        thread = await self._document_thread(user_id, document.id)
        if await self._runner.paused(str(thread.id)):
            return SkippedTurn(
                document_id=document.id,
                reason="Its chat waits for the user to answer a question",
            )
        try:
            await self.send(user_id, thread.id, text, timezone)
        except Conflict:
            return SkippedTurn(
                document_id=document.id,
                reason="Its chat is already working on a reply",
            )
        return StartedTurn(document_id=document.id, title=document.title)


__all__ = ["ConversationService"]
