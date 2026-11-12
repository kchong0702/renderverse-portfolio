from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import Completed, EzcareerClient, Failed, InputRequired
from src.core.config import DocumentsSettings, ProfileSettings
from src.core.exceptions import InvalidInput, NotFound, ServiceUnavailable
from src.features.profile.enums import ImportSource
from src.features.profile.export import read_export
from src.features.profile.resume import resume_profile
from src.features.profile.schemas import (
    ImportedProfile,
    ImportedResume,
    ImportProfileInput,
    NetworkingCopy,
    NetworkingRead,
    NetworkingWrite,
    ProfileImportRead,
    ResumeFile,
    WriteNetworkingInput,
)
from src.features.profile.service import ProfileService
from src.features.settings import SettingsService


class ProfileRunService:
    def __init__(
        self,
        session: AsyncSession,
        profile: ProfileService,
        settings: SettingsService,
        ezcareer: EzcareerClient,
        limits: ProfileSettings,
        documents: DocumentsSettings,
    ):
        """Hold the session, the profile and settings services, the harness and the
        upload limits for imports and résumés"""
        self._session = session
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer
        self._limits = limits
        self._documents = documents

    async def _run[R](
        self, executable: str, reply: type[R], user_id: UUID, data: BaseModel
    ) -> R:
        """Run a harness workflow with no transaction open and return its reply;
        InvalidInput with the reason when it fails"""
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        match await self._ezcareer.send(
            executable,
            reply,
            user_id=user_id,
            context_id=f"{user_id}:{uuid4()}",
            data=data,
            metadata=metadata,
        ):
            case Completed(reply=result):
                return result
            case InputRequired():
                raise ServiceUnavailable(
                    f"{executable} asked for input ops cannot give"
                )
            case Failed(reason=reason):
                raise InvalidInput(reason)

    async def upload(
        self, user_id: UUID, filename: str, media_type: str, content: bytes
    ) -> ProfileImportRead:
        """Import a résumé (PDF or Word) or a profile export (.zip) into the profile;
        the same file again returns its earlier import"""
        export = media_type in self._limits.export_types
        if not export and media_type not in self._documents.upload_types:
            raise InvalidInput("Upload a PDF, Word (.docx) or .zip file")
        limit = (
            self._limits.max_export_bytes
            if export
            else self._documents.max_upload_bytes
        )
        if not content or len(content) > limit:
            raise InvalidInput(
                f"The file must be between 1 byte and {limit // (1024 * 1024)} MB"
            )
        if (earlier := await self._profile.imported(user_id, content)) is not None:
            return earlier
        if export:
            read = read_export(content, self._limits.max_unzipped_bytes)
            imported = await self._run(
                "import-profile",
                ImportedProfile,
                user_id,
                ImportProfileInput(files=read.files),
            )
            imported.about = imported.about.model_copy(
                update={"name": read.name, "email": read.email, "phone": read.phone}
            )
        else:
            imported = resume_profile(
                (
                    await self._run(
                        "import-resume",
                        ImportedResume,
                        user_id,
                        ResumeFile(file=content),
                    )
                ).document.content
            )
        return await self._profile.sync(
            user_id, ImportSource.DATA, filename, media_type, content, imported
        )

    async def write_networking(
        self, user_id: UUID, request: NetworkingWrite
    ) -> NetworkingRead:
        """Write the Networking copy from every fact, archived ones included, or
        only its headline, summary or one role's or project's description"""
        facts = await self._profile.networking_facts(user_id)
        if request.only not in (None, "headline", "summary"):
            if not request.only.startswith(("role-", "project-")):
                raise InvalidInput(
                    "Only the headline, the summary or a role's or project's"
                    " description can be rewritten"
                )
            if request.only not in {fact.id for fact in facts}:
                raise NotFound("No such fact")
        written = await self._run(
            "write-networking",
            NetworkingCopy,
            user_id,
            WriteNetworkingInput(aim=request.aim, facts=facts, only=request.only),
        )
        return await self._profile.keep_networking(
            user_id, request.aim, written, request.only
        )


__all__ = ["ProfileRunService"]
