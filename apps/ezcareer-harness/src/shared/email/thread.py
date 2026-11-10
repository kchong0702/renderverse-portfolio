from src.shared.email.types import EmailThread


def untrusted_thread(thread: EmailThread) -> str:
    """The thread as text an agent reads as data, each message with its sender and
    time"""
    messages = "\n\n".join(
        f"From: {message.sender}\nSent: {message.sent_at.isoformat()}\n{message.text}"
        for message in thread.messages
    )
    return f"<thread untrusted>\nSubject: {thread.subject}\n\n{messages}\n</thread>"
