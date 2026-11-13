from __future__ import annotations

import re
from html.parser import HTMLParser

from src.clients.google import GmailPart, GmailThread
from src.features.inbox.schemas import ThreadContent, ThreadMessage


class _TextParser(HTMLParser):
    def __init__(self):
        """Collect an HTML body's text, leaving out styles and scripts"""
        super().__init__()
        self.parts: list[str] = []
        self._hidden = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Hide a style or script's text; a br starts a new line"""
        if tag in ("style", "script"):
            self._hidden = True
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Show text again after a style or script; a block ends its line"""
        if tag in ("style", "script"):
            self._hidden = False
        elif tag in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Keep text that is not inside a style or script"""
        if not self._hidden:
            self.parts.append(data)


def _html_text(markup: str) -> str:
    """The readable text of an HTML body: no styles, scripts or tags"""
    parser = _TextParser()
    parser.feed(markup)
    parser.close()
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()


def message_text(part: GmailPart) -> str:
    """A message's body as plain text; HTML-only mail is reduced to its text"""
    return part.find("text/plain").strip() or _html_text(part.find("text/html"))


def thread_content(thread: GmailThread) -> ThreadContent:
    """A Gmail thread as the harness reads it"""
    return ThreadContent(
        subject=thread.messages[0].payload.header("Subject"),
        messages=[
            ThreadMessage(
                sender=m.payload.header("From"),
                sent_at=m.internal_date,
                text=message_text(m.payload),
            )
            for m in thread.messages
        ],
    )


__all__ = ["message_text", "thread_content"]
