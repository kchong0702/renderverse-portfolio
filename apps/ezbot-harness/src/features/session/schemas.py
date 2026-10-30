from pydantic import BaseModel


class Session(BaseModel):
    """Session created for this tab, owned by the browser cookie"""

    session_id: str
    """Send back in the session header with every chat request from this tab"""

    idle_ttl_s: int
    """Seconds of inactivity before the session and its history are deleted"""
