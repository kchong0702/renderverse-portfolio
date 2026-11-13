from __future__ import annotations

import asyncio
import html
from base64 import urlsafe_b64encode
from collections.abc import Sequence
from contextlib import suppress
from datetime import UTC, date, datetime, timedelta
from email.message import EmailMessage
from email.utils import parseaddr
from hashlib import sha256
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import (
    Completed,
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
from src.core.agent_runner import AgentRunner
from src.core.config import GoogleSettings
from src.core.exceptions import (
    AlreadyExists,
    InvalidInput,
    NotFound,
    ServiceUnavailable,
)
from src.core.logging import get_logger
from src.db.base import as_utc, utcnow
from src.features.applications.enums import NextStepFormat, StepKind, StepStatus
from src.features.applications.models import Application, ApplicationStep
from src.features.applications.repository import ApplicationRepository
from src.features.calendar import CalendarService
from src.features.calendar.schemas import EventCreate
from src.features.google import GoogleService
from src.features.inbox.content import message_text, thread_content
from src.features.inbox.enums import ThreadState
from src.features.inbox.models import EmailThread
from src.features.inbox.repository import InboxRepository
from src.features.inbox.schemas import (
    DraftApplication,
    DraftReplyInput,
    DraftReplyOutput,
    EmailCreate,
    FollowUpDraft,
    InboxList,
    InboxMessage,
    InboxMessageDetail,
    ReplyCreate,
    TriageApplication,
    TriageEmailInput,
    TriageEmailOutput,
)
from src.features.profile import ProfileService
from src.features.settings import SettingsService

logger = get_logger(__name__)


def _emailed(step: ApplicationStep) -> datetime | date | None:
    """When its email thread last said the step happens: its start in UTC, or else
    its due day"""
    return as_utc(step.email_starts_at) if step.email_starts_at else step.email_due_on


def _summary(
    message: GmailMessage, thread: EmailThread | None, steps: Sequence[ApplicationStep]
) -> InboxMessage:
    """The list row for a Gmail message, with its thread's triage and what the steps
    triage found in the thread say"""
    name, email = parseaddr(message.payload.header("From"))
    found = [s for s in steps if thread and s.email_thread_id == thread.id]
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
        decide_by=min(
            (
                s.due_on
                for s in found
                if s.kind is StepKind.OFFER_DEADLINE
                and s.status is StepStatus.OPEN
                and s.due_on
            ),
            default=None,
        ),
        application_id=thread.application_id if thread else None,
        on_calendar=any(
            s.kind is StepKind.INTERVIEW and s.event_id is not None for s in found
        ),
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
        google: GoogleService,
        settings: SettingsService,
        calendar: CalendarService,
        profile: ProfileService,
        client: GoogleClient,
        runner: AgentRunner,
        config: GoogleSettings,
    ):
        """Read and send Gmail with the user's token, triage and draft through the agent
        runner, and keep the triage through a repository on the session"""
        self._session = session
        self._repository = InboxRepository(session)
        self._applications = ApplicationRepository(session)
        self._google = google
        self._settings = settings
        self._calendar = calendar
        self._profile = profile
        self._client = client
        self._runner = runner
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
            run = await self._runner.run(
                user_id,
                "triage-email",
                TriageEmailOutput,
                data=TriageEmailInput(
                    thread=thread_content(thread), applications=applications
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

    async def _keep_step(
        self, thread: EmailThread, kind: StepKind, **found: object
    ) -> None:
        """Move the thread's upcoming open step of the kind to a time the thread had not
        given before, or else add the found step as a new round"""
        step = ApplicationStep(
            user_id=thread.user_id,
            application_id=thread.application_id,
            email_thread_id=thread.id,
            kind=kind,
            email_starts_at=found.get("starts_at"),
            email_due_on=found.get("due_on"),
            **found,
        )
        kept = [
            s
            for s in await self._applications.thread_steps(thread.user_id, [thread.id])
            if s.kind is kind
        ]
        if any(_emailed(s) == _emailed(step) for s in kept):
            return
        now = utcnow()
        today = now.astimezone(
            ZoneInfo(await self._settings.timezone(thread.user_id) or "UTC")
        ).date()
        current = next(
            (
                s
                for s in kept
                if s.status is StepStatus.OPEN
                and (as_utc(s.starts_at) > now if s.starts_at else s.due_on >= today)
            ),
            None,
        )
        if current is None:
            await self._applications.add(step)
            return
        for field, value in found.items():
            setattr(current, field, value)
        current.email_starts_at = step.email_starts_at
        current.email_due_on = step.email_due_on
        if current.event_id and step.starts_at:
            await self._calendar.move(
                thread.user_id, current.event_id, step.starts_at, step.ends_at
            )

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
            TriageApplication(
                id=application.id,
                company=application.job.company,
                role=application.job.title,
            )
            for application in await self._applications.applications(user_id)
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
            application_id = next(
                (a.id for a in applications if a.id == result.application_id), None
            )
            thread = await self._repository.save(
                user_id,
                message.thread_id,
                last_message_id=message.id,
                state=result.state,
                application_id=application_id,
            )
            threads[message.thread_id] = thread
            if application_id is not None:
                await self._applications.link_thread_steps(thread.id, application_id)
            if interview := result.interview:
                start = interview.start.astimezone(UTC)
                await self._keep_step(
                    thread,
                    StepKind.INTERVIEW,
                    starts_at=start,
                    ends_at=interview.end.astimezone(UTC)
                    if interview.end and interview.end > start
                    else None,
                    format=NextStepFormat(interview.format)
                    if interview.format
                    else None,
                    location=interview.location,
                )
            if result.decide_by:
                await self._keep_step(
                    thread, StepKind.OFFER_DEADLINE, due_on=result.decide_by
                )
        await self._session.commit()

    async def _add_interviews(
        self, user_id: UUID, steps: Sequence[ApplicationStep]
    ) -> None:
        """Put each upcoming open interview step triage found on Google Calendar,
        once"""
        for step in steps:
            if (
                step.kind is not StepKind.INTERVIEW
                or step.status is not StepStatus.OPEN
                or step.starts_at is None
                or step.event_id
            ):
                continue
            start = as_utc(step.starts_at)
            if start <= utcnow():
                continue
            event_id = sha256(
                f"{user_id}:{step.email_thread_id}:{_emailed(step)}".encode()
            ).hexdigest()
            if not await self._applications.claim_event(step, event_id):
                continue
            application = (
                await self._applications.owned(
                    Application, user_id, step.application_id
                )
                if step.application_id
                else None
            )
            with suppress(AlreadyExists):
                await self._calendar.create(
                    user_id,
                    EventCreate(
                        title=f"{application.job.company} {application.job.title} interview"
                        if application
                        else "Interview",
                        start=start,
                        end=as_utc(step.ends_at)
                        if step.ends_at
                        else start + timedelta(minutes=self._config.interview_minutes),
                        location=step.location,
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
        steps = await self._applications.thread_steps(
            user_id, [t.id for t in threads.values()]
        )
        if (await self._settings.get(user_id)).automation.add_interview_invites:
            await self._add_interviews(user_id, steps)
        return InboxList(
            messages=[_summary(m, threads.get(m.thread_id), steps) for m in found],
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
        steps = (
            await self._applications.thread_steps(user_id, [thread.id])
            if thread
            else []
        )
        return InboxMessageDetail(
            **_summary(message, thread, steps).model_dump(),
            to=message.payload.header("To"),
            body=message_text(message.payload),
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
        run = await self._runner.run(
            user_id,
            "draft-reply",
            DraftReplyOutput,
            data=DraftReplyInput(
                thread=thread_content(thread) if thread else None,
                application=DraftApplication(
                    company=application.job.company,
                    role=application.job.title,
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
