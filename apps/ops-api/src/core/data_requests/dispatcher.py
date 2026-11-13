from functools import partial
from uuid import UUID

from pydantic import BaseModel, ValidationError

from src.clients.ezcareer import AnswerDataRequest, DataRequest
from src.core.data_requests.schemas import DataRequestKinds, FetchError
from src.core.logging import get_logger

logger = get_logger(__name__)


class DataRequestDispatcher:
    def __init__(self, *tables: DataRequestKinds):
        """Answer every kind these tables map"""
        self._kinds = {kind: entry for table in tables for kind, entry in table.items()}

    async def _answer(self, user_id: UUID, request: DataRequest) -> BaseModel:
        """The answer to a paused run's data request for the user; FetchError for an
        unknown kind or a malformed request"""
        match self._kinds.get(request.fetch):
            case None:
                answer = FetchError(error=f"Ops can't answer {request.fetch}")
                outcome = "unknown"
            case kind:
                try:
                    parsed = kind.request.model_validate(request.model_dump())
                except ValidationError as error:
                    answer = FetchError(error=str(error))
                    outcome = "malformed"
                else:
                    answer = await kind.answer(user_id, parsed)
                    outcome = (
                        "refused" if isinstance(answer, FetchError) else "answered"
                    )
        logger.info(
            "data_request", kind=request.fetch, user_id=str(user_id), outcome=outcome
        )
        return answer

    def for_user(self, user_id: UUID) -> AnswerDataRequest:
        """Answers the data requests of a run for this user"""
        return partial(self._answer, user_id)
