from src.core.types import NextStep


class ExecuteError(Exception):
    def __init__(self, reason: str, next_step: NextStep | None = None) -> None:
        """A run cannot finish; the client sees reason, and next_step when the user
        must add something first"""
        super().__init__(reason)
        self.next_step = next_step
        """What the user must do before the run can work"""
