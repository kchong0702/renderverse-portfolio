from __future__ import annotations

from src.clients.ezcareer.schemas import NextScreen
from src.core.exceptions import ServiceException


class AgentRunFailed(ServiceException):
    status_code = 422
    """The run could not reply for this input"""

    def __init__(self, reason: str, next_screen: NextScreen | None):
        """Keep the harness's reason as the message, and the screen where the user
        adds what the run lacked"""
        super().__init__(reason)
        self.next = next_screen
        """Where the user adds what the run lacked; None when nothing would help"""


__all__ = ["AgentRunFailed"]
