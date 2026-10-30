from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from src.core.config import get_settings
from src.features.intent.models import IntentType

_settings = get_settings()

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Text
    """User's latest message; the server keeps the conversation"""

    @field_validator("message")
    @classmethod
    def _validate_message(cls, v: str) -> str:
        max_chars = _settings.chat.max_message_chars
        if len(v) > max_chars:
            raise ValueError(
                f"message accepts at most {max_chars} characters, got {len(v)}"
            )
        return v


class ResponseEvent(BaseModel):
    """One Server-Sent Event of a response; `type` is also the SSE event name"""

    type: str
    """Event type, e.g. `response.output_text.delta`"""


class OutputTextDelta(ResponseEvent):
    """The next piece of the response's text, to append to what came before"""

    type: Literal["response.output_text.delta"] = "response.output_text.delta"
    """Event type"""

    delta: str
    """Text added since the previous delta"""


class ResponseIntent(ResponseEvent):
    """Sent after the response's text: offer a button to this section"""

    type: Literal["response.intent"] = "response.intent"
    """Event type"""

    intent_type: IntentType
    """Portfolio section the button takes the visitor to"""


class ResponseCompleted(ResponseEvent):
    """The response finished; no more events follow"""

    type: Literal["response.completed"] = "response.completed"
    """Event type"""


class ResponseCancelled(ResponseEvent):
    """The visitor stopped the response; no more events follow"""

    type: Literal["response.cancelled"] = "response.cancelled"
    """Event type"""


class ResponseError(BaseModel):
    """Why a response failed"""

    code: str
    """Machine-readable error code, e.g. `CHAT_FAILED`"""

    message: str
    """Human-readable description of the error"""


class ResponseFailed(ResponseEvent):
    """The bot failed to response; no more events follow"""

    type: Literal["response.failed"] = "response.failed"
    """Event type"""

    error: ResponseError
    """Why the response failed"""
