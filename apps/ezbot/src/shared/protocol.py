from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.language_models import BaseChatModel

from src.core.config import ModelSettings


@runtime_checkable
class Interruptible(Protocol):
    """Work in progress that can be stopped, such as a bot response"""

    @property
    def done(self) -> bool:
        """Whether the work has finished"""
        ...

    def stop(self) -> None:
        """Cancel the work if it is still running"""
        ...


class ModelAdapter(Protocol):
    """Builds chat models for one provider"""

    def create(self, spec: ModelSettings) -> BaseChatModel:
        """Build the chat model described by `spec`"""
        ...


__all__ = ["Interruptible", "ModelAdapter"]
