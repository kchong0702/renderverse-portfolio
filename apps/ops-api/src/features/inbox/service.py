from __future__ import annotations

import asyncio
import html
import re
from base64 import urlsafe_b64encode
from contextlib import suppress
from datetime import UTC, timedelta
from email.message import EmailMessage
from email.utils import parseaddr
from hashlib import sha256
from html.parser import HTMLParser
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.ezcareer import (
    Completed,
    DataRequest,
    EzcareerClient,
    Failed,
    InputRequired,
    RunMetadata,
)
from src.clients.google import (
    GmailMessage,
    GmailPart,
    GmailSend,
    GmailThread,
    GoogleClient,
)
from src.core.config import GoogleSettings, get_settings
from src.core.exceptions import (
    AlreadyExists,
    InvalidInput,
    NotFound,
    ServiceException,
    ServiceUnavailable,
)
from src.core.logging import get_logger
from src.db.base import aware, utcnow
from src.db.session import session_scope
from src.features.applications.models import Application
from src.features.applications.repository import ApplicationRepository
from src.features.calendar import CalendarService
from src.features.calendar.schemas import EventCreate, FreeSlots
from src.features.documents.schemas import FetchError
from src.features.google import GoogleService
from src.features.inbox.enums import ThreadState
from src.features.inbox.models import EmailThread
from src.features.inbox.repository import InboxRepository
from src.features.inbox.schemas import (
    DraftApplication,
    DraftReplyInput,
    DraftReplyOutput,
    EmailCreate,
    FollowUpDraft,
    FreeSlotsRequest,
    InboxList,
    InboxMessage,
    InboxMessageDetail,
    ReplyCreate,
    ThreadAnswer,
    ThreadContent,
    ThreadMessage,
    ThreadRequest,
    TriageApplication,
    TriageEmailInput,
    TriageEmailOutput,
)
from src.features.profile import ProfileService
from src.features.settings import SettingsService

logger = get_logger(__name__)


def _summary(message: GmailMessage, thread: EmailThread | None) -> InboxMessage:
    """The list row for a Gmail message, with its thread's triage"""
    name, email = parseaddr(message.payload.header("From"))
    return InboxMessage(
        id=message.id,
        thread_id=message.thread_id,
        from_name=name or email,
        from_email=email,
        subject=message.payload.header("Subject"),
        snippet=html.unescape(message.snippet),
        received_at=message.internal_date,
        unread="UNREAD" in message.label_ids,
        state=thread.state if thread else None,
        decide_by=thread.decide_by if thread else None,
        application_id=thread.application_id if thread else None,
    )


class _TextParser(HTMLParser):
    def __init__(self):
        """Collect an HTML body's text, leaving out styles and scripts"""
        super().__init__()
        self.parts: list[str] = []
        self._hidden = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Hide a style or script's text; a br starts a new line"""
        if tag in ("style", "script"):
            self._hidden = True
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Show text again after a style or script; a block ends its line"""
        if tag in ("style", "script"):
            self._hidden = False
        elif tag in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Keep text that is not inside a style or script"""
        if not self._hidden:
            self.parts.append(data)


def _html_text(markup: str) -> str:
    """The readable text of an HTML body: no styles, scripts or tags"""
    parser = _TextParser()
    parser.feed(markup)
    parser.close()
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()


def _text(part: GmailPart) -> str:
    """A message's body as plain text; HTML-only mail is reduced to its text"""
    return part.find("text/plain").strip() or _html_text(part.find("text/html"))


def _content(thread: GmailThread) -> ThreadContent:
    """A Gmail thread as the harness workflows read it"""
    return ThreadContent(
        subject=thread.messages[0].payload.header("Subject"),
        messages=[
            ThreadMessage(
                sender=m.payload.header("From"),
                sent_at=m.internal_date,
                text=_text(m.payload),
            )
            for m in thread.messages
        ],
    )


def _mime(to: str, subject: str, body: str, answers: GmailPart | None = None) -> str:
    """An email as Gmail's send takes it, RFC 2822 and base64url encoded; a reply
    names the message it answers so mail clients thread it"""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    if answers is not None:
        message_id = answers.header("Message-ID")
        message["In-Reply-To"] = message_id
        message["References"] = f"{answers.header('References')} {message_id}".strip()
    message.set_content(body)
    return urlsafe_b64encode(message.as_bytes()).decode()


class InboxService:
    def __init__(
        self,
        session: AsyncSession,
        factory: async_sessionmaker[AsyncSession],
        google: GoogleService,
        settings: SettingsService,
        calendar: CalendarService,
        profile: ProfileService,
        client: GoogleClient,
        ezcareer: EzcareerClient,
        config: GoogleSettings,
    ):
        """Read and send Gmail with the user's token, triage threads and draft emails
        with the harness, and keep the triage through a repository on the session"""
        self._session = session
        self._factory = factory
        self._repository = InboxRepository(session)
        self._applications = ApplicationRepository(session)
        self._google = google
        self._settings = settings
        self._calendar = calendar
        self._profile = profile
        self._client = client
        self._ezcareer = ezcareer
        self._config = config

    async def _triage(
        self,
        user_id: UUID,
        token: str,
        thread_id: str,
        applications: list[TriageApplication],
        metadata: RunMetadata | None,
    ) -> TriageEmailOutput | None:
        """triage-email's reading of the thread; None when it could not run, so the
        next sync tries again"""
        try:
            thread = await self._client.thread(token, thread_id)
            run = await self._ezcareer.send(
                "triage-email",
                TriageEmailOutput,
                user_id=user_id,
                context_id=f"{user_id}:{uuid4()}",
                data=TriageEmailInput(
                    thread=_content(thread), applications=applications
                ),
                metadata=metadata,
            )
        except (NotFound, ServiceUnavailable) as error:
            logger.warning("triage_skipped", thread_id=thread_id, reason=error.message)
            return None
        if not isinstance(run, Completed):
            logger.warning("triage_failed", thread_id=thread_id, status=run.status)
            return None
        return run.reply

    async def _sync(
        self,
        user_id: UUID,
        token: str,
        changed: list[GmailMessage],
        threads: dict[str, EmailThread],
    ) -> None:
        """Triage the threads of these newest messages and store what triage-email
        read in threads; a thread it could not read is left for the next sync"""
        applications = [
            TriageApplication.model_validate(a, from_attributes=True)
            for a, _ in await self._applications.applications(user_id)
        ]
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        results = await asyncio.gather(
            *(
                self._triage(user_id, token, m.thread_id, applications, metadata)
                for m in changed
            )
        )
        for message, result in zip(changed, results, strict=True):
            if result is None:
                continue
            interview = result.interview
            start = interview.start.astimezone(UTC) if interview else None
            threads[message.thread_id] = await self._repository.save(
                user_id,
                message.thread_id,
                last_message_id=message.id,
                state=result.state,
                application_id=next(
                    (a.id for a in applications if a.id == result.application_id), None
                ),
                decide_by=result.decide_by,
                interview_start=start,
                interview_end=interview.end.astimezone(UTC)
                if interview and start and interview.end and interview.end > start
                else None,
                interview_location=interview.location if interview else None,
            )
        await self._session.commit()

    async def _add_interviews(
        self, user_id: UUID, newest: list[GmailMessage], threads: dict[str, EmailThread]
    ) -> None:
        """Put each upcoming interview a thread confirms on Google Calendar, once"""
        for message in newest:
            thread = threads.get(message.thread_id)
            if thread is None or thread.interview_start is None or thread.event_id:
                continue
            start = aware(thread.interview_start)
            if start <= utcnow():
                continue
            event_id = sha256(f"{user_id}:{message.thread_id}".encode()).hexdigest()
            if not await self._repository.claim_event(thread, event_id):
                continue
            application = (
                await self._applications.owned(
                    Application, user_id, thread.application_id
                )
                if thread.application_id
                else None
            )
            with suppress(AlreadyExists):
                await self._calendar.create(
                    user_id,
                    EventCreate(
                        title=f"{application.company} {application.role} interview"
                        if application
                        else "Interview",
                        start=start,
                        end=aware(thread.interview_end)
                        if thread.interview_end
                        else start + timedelta(minutes=self._config.interview_minutes),
                        location=thread.interview_location,
                    ),
                    event_id,
                )

    async def messages(self, user_id: UUID) -> InboxList:
        """The newest emails that match the job-search query with their threads'
        triage; new or changed threads are triaged first"""
        token = await self._google.access_token(user_id)
        found = await self._client.messages(
            token, self._config.inbox_query, self._config.inbox_limit
        )
        newest: dict[str, GmailMessage] = {}
        for message in found:
            newest.setdefault(message.thread_id, message)
        threads = {
            t.thread_id: t
            for t in await self._repository.threads(user_id, list(newest))
        }
        changed = [
            m
            for m in newest.values()
            if m.thread_id not in threads
            or threads[m.thread_id].last_message_id != m.id
        ]
        if changed:
            await self._sync(user_id, token, changed, threads)
        if (await self._settings.get(user_id)).automation.add_interview_invites:
            await self._add_interviews(user_id, list(newest.values()), threads)
        return InboxList(
            messages=[_summary(m, threads.get(m.thread_id)) for m in found],
            needs_reply=sum(
                1 for t in threads.values() if t.state is ThreadState.NEEDS_REPLY
            ),
        )

    async def message(self, user_id: UUID, message_id: str) -> InboxMessageDetail:
        """One email with its body as plain text and its thread's triage"""
        token = await self._google.access_token(user_id)
        message = await self._client.message(token, message_id)
        thread = next(
            iter(await self._repository.threads(user_id, [message.thread_id])), None
        )
        return InboxMessageDetail(
            **_summary(message, thread).model_dump(),
            to=message.payload.header("To"),
            body=_text(message.payload),
        )

    async def _draft(
        self,
        user_id: UUID,
        thread: GmailThread | None,
        application: Application | None,
    ) -> DraftReplyOutput | Failed:
        """Run draft-reply on the thread or the application and the profile's facts,
        offering free slots for a thread while the user lets it"""
        settings = await self._settings.get(user_id)
        free = await self._calendar.free_slots(
            user_id, settings.scheduling, self._config.free_slot_days
        )
        offered = (
            free.free_slots if thread and settings.automation.offer_free_slots else []
        )
        facts = (await self._profile.agent_profile(user_id)).facts
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        run = await self._ezcareer.send(
            "draft-reply",
            DraftReplyOutput,
            user_id=user_id,
            context_id=f"{user_id}:{uuid4()}",
            data=DraftReplyInput(
                thread=_content(thread) if thread else None,
                application=DraftApplication(
                    company=application.company,
                    role=application.role,
                    stage=application.stage,
                    applied_at=application.applied_on,
                )
                if application
                else None,
                free_slots=offered,
                timezone=free.timezone,
                facts=facts,
            ),
            metadata=metadata,
        )
        match run:
            case Completed(reply=reply):
                return reply.model_copy(
                    update={"slots": [s for s in reply.slots if s in offered]}
                )
            case InputRequired():
                raise ServiceUnavailable("draft-reply asked for input ops cannot give")
            case Failed():
                return run

    async def draft_reply(
        self, user_id: UUID, thread_id: str
    ) -> DraftReplyOutput | Failed:
        """A reply to the thread with the free slots it offers; nothing is sent"""
        token = await self._google.access_token(user_id)
        thread = await self._client.thread(token, thread_id)
        stored = next(iter(await self._repository.threads(user_id, [thread_id])), None)
        application = (
            await self._applications.owned(Application, user_id, stored.application_id)
            if stored and stored.application_id
            else None
        )
        return await self._draft(user_id, thread, application)

    async def draft_follow_up(
        self, user_id: UUID, application_id: UUID
    ) -> FollowUpDraft | Failed:
        """A follow-up for an application with no reply; nothing is sent"""
        application = await self._applications.owned(
            Application, user_id, application_id
        )
        if application is None:
            raise NotFound("No such application")
        run = await self._draft(user_id, None, application)
        return (
            FollowUpDraft(body=run.body) if isinstance(run, DraftReplyOutput) else run
        )

    async def answer_data_request(
        self, user_id: UUID, request: DataRequest
    ) -> ThreadAnswer | FreeSlots | FetchError:
        """A paused run's thread or free slots, on a session of its own"""
        try:
            parsed = TypeAdapter(ThreadRequest | FreeSlotsRequest).validate_python(
                request.model_dump()
            )
        except ValidationError as error:
            return FetchError(error=str(error))
        async for session in session_scope(self._factory):
            google = GoogleService(session, self._client, self._config)
            try:
                match parsed:
                    case ThreadRequest(id=thread_id):
                        answer = ThreadAnswer(
                            thread=_content(
                                await self._client.thread(
                                    await google.access_token(user_id), thread_id
                                )
                            )
                        )
                    case FreeSlotsRequest(days=days):
                        settings = await SettingsService(
                            session, self._ezcareer, google, get_settings().jsearch
                        ).get(user_id)
                        free = await CalendarService(
                            google, self._client, self._config
                        ).free_slots(user_id, settings.scheduling, days)
                        answer = (
                            free
                            if settings.automation.offer_free_slots
                            else free.model_copy(update={"free_slots": []})
                        )
            except ServiceException as error:
                answer = FetchError(error=error.message)
        return answer

    async def reply(self, user_id: UUID, thread_id: str, reply: ReplyCreate) -> None:
        """Answer the newest email in the thread that someone else sent, in the thread"""
        token = await self._google.access_token(user_id)
        thread = await self._client.thread(token, thread_id)
        me = (await self._google.email(user_id) or "").lower()
        theirs = [
            m.payload
            for m in thread.messages
            if parseaddr(m.payload.header("From"))[1].lower() != me
        ]
        if not theirs:
            raise InvalidInput(
                "Nobody else wrote in this thread, so there is no one to reply to"
            )
        subject = thread.messages[0].payload.header("Subject")
        await self._client.send(
            token,
            GmailSend(
                raw=_mime(
                    theirs[-1].header("Reply-To") or theirs[-1].header("From"),
                    subject if subject.lower().startswith("re:") else f"Re: {subject}",
                    reply.body,
                    theirs[-1],
                ),
                thread_id=thread_id,
            ),
        )

    async def send(self, user_id: UUID, email: EmailCreate) -> None:
        """Send a new email from the user's Gmail"""
        token = await self._google.access_token(user_id)
        await self._client.send(
            token, GmailSend(raw=_mime(email.to, email.subject, email.body))
        )


__all__ = ["InboxService"]
