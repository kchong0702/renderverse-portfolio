from __future__ import annotations

from typing import Literal

ModelFamily = Literal["claude", "glm", "openai"]
"""A model provider ezcareer-harness can run"""


__all__ = ["ModelFamily"]
