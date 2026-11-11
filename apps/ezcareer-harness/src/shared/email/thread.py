from src.shared.email.types import EmailThread


def untrusted_thread(thread: EmailThread) -> str:
    """The thread as text an agent reads as data, each message with its sender and
    time"""
    messages = "\n\n".join(
        f"From: {message.sender}\nSent: {message.sent_at.isoformat()}\n{message.text}"
        for message in thread.messages
    )
    return f"<thread untrusted>\nSubject: {thread.subject}\n\n{messages}\n</thread>"


def latest_messages(
    thread: EmailThread, max_messages: int, max_chars: int
) -> EmailThread:
    """The thread with only its latest max_messages messages, each cut to
    max_chars and marked [cut]"""
    return thread.model_copy(
        update={
            "messages": [
                message.model_copy(update={"text": f"{message.text[:max_chars]} [cut]"})
                if len(message.text) > max_chars
                else message
                for message in thread.messages[-max_messages:]
            ]
        }
    )
