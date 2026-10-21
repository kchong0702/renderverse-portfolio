from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from src.core.config import get_settings

_settings = get_settings()

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def _check_length(v: str, max_chars: int) -> str:
    if len(v) > max_chars:
        raise ValueError(
            f"message accepts at most {max_chars} characters, got {len(v)}"
        )
    return v


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    """Author of the message"""

    content: Text
    """Message content"""

    @model_validator(mode="after")
    def _validate_content(self) -> "Message":
        chat = _settings.chat
        max_chars = (
            chat.max_message_chars if self.role == "user" else chat.max_reply_chars
        )
        _check_length(self.content, max_chars)
        return self


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Text
    """User's latest message"""

    history: list[Message] = Field(default_factory=list)
    """Prior conversation, oldest first"""

    @field_validator("message")
    @classmethod
    def _validate_message(cls, v: str) -> str:
        return _check_length(v, _settings.chat.max_message_chars)

    @field_validator("history")
    @classmethod
    def _validate_history(cls, v: list[Message]) -> list[Message]:
        max_history = _settings.chat.max_history
        if len(v) > max_history:
            raise ValueError(
                f"history accepts at most {max_history} messages, got {len(v)}"
            )
        return v


class Token(BaseModel):
    """`token` event, a chunk of the bot reply"""

    content: str


class Done(BaseModel):
    """`done` event, the bot reply is complete"""

    finish_reason: Literal["stop"]


class Error(BaseModel):
    """`error` event, the bot failed to reply"""

    model_config = ConfigDict(extra="ignore")

    status_code: int
    """Error status code (e.g 400, 500)"""

    code: str
    """Error code in text"""

    message: str
    """Error message"""
