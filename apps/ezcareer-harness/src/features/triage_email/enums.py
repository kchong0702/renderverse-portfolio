from enum import StrEnum


class ThreadState(StrEnum):
    NEEDS_REPLY = "needs_reply"
    """The latest message asks the user something or waits on them"""

    INTERVIEW = "interview"
    """The thread confirms an interview at a set time"""

    OFFER = "offer"
    """The thread offers the user a job"""

    INFO = "info"
    """Nothing for the user to answer or plan"""


class InterviewFormat(StrEnum):
    VIDEO = "video"
    """On a video call"""

    PHONE = "phone"
    """On the phone"""

    ON_SITE = "on_site"
    """At the employer's office"""
