from src.shared.jobs.types import PostingLine


def posting_lines(text: str) -> list[PostingLine]:
    """The text's lines, stripped, without empty ones, numbered from one"""
    texts = (line.strip() for line in text.splitlines())
    return [
        PostingLine(id=number, text=text)
        for number, text in enumerate(filter(None, texts), start=1)
    ]
