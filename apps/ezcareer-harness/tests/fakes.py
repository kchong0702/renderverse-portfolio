from typing import Any, override

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from pydantic import Field


class FakeModel(GenericFakeChatModel):
    prompts: list[list[BaseMessage]] = Field(default_factory=list)
    """Messages of every call, in order"""

    @override
    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeModel":
        """Answers with the scripted messages whatever tools are bound"""
        return self

    @override
    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        """Records the messages, then returns the next scripted reply"""
        self.prompts.append(messages)
        return super()._generate(messages, *args, **kwargs)


def replying(*replies: dict[str, Any]) -> FakeModel:
    """A model that answers each call with the next ResumeImport"""
    return FakeModel(
        messages=iter(
            AIMessage(
                "", tool_calls=[{"name": "ResumeImport", "args": reply, "id": str(n)}]
            )
            for n, reply in enumerate(replies)
        )
    )
